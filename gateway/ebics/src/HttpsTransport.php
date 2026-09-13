<?php
declare(strict_types=1);

namespace KT\Banking;

use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;
use InvalidArgumentException;
use RuntimeException;
use XMLReader;

// Endpoint and CA bundle must come from trusted server configuration, never a request.
final readonly class HttpsTransport implements HttpClientInterface
{
    public const MAX_RESPONSE_BYTES = 8388608;
    public const MAX_HEADER_BYTES = 65536;
    public const MAX_REQUEST_BYTES = 1048576;
    public const MAX_XML_NODES = 4096;
    public const MAX_XML_DEPTH = 64;
    public const MAX_XML_ATTRIBUTES = 128;
    private ?string $caBundle;

    public function __construct(private string $endpoint, ?string $caBundle = null, private int $timeoutMs = 30000)
    {
        $parts = parse_url($endpoint);
        if (!is_array($parts) || ($parts['scheme'] ?? '') !== 'https' || empty($parts['host'])
            || empty($parts['path']) || isset($parts['user']) || isset($parts['pass'])
            || isset($parts['query']) || isset($parts['fragment']) || preg_match('/[\x00-\x20\x7f]/', $endpoint)
            || !filter_var($endpoint, FILTER_VALIDATE_URL) || $timeoutMs < 100 || $timeoutMs > 30000) {
            throw new InvalidArgumentException('Invalid configured bank HTTPS endpoint or timeout');
        }
        $this->caBundle = $caBundle === null ? null : (realpath($caBundle) ?: null);
        if ($caBundle !== null && ($this->caBundle === null || !is_file($this->caBundle) || !is_readable($this->caBundle))) {
            throw new InvalidArgumentException('Configured bank CA bundle is unavailable');
        }
        if (!defined('LIBXML_NO_XXE')) throw new RuntimeException('External-entity protection requires libxml 2.13 or later');
    }

    public function post(string $url, Request $request): Response
    {
        if ($url !== $this->endpoint) throw new RuntimeException('Bank endpoint differs from trusted binding');
        $content = $request->getContent();
        if (strlen($content) > self::MAX_REQUEST_BYTES) throw new RuntimeException('Bank request exceeds size limit');
        $body = '';
        $headerBytes = 0;
        $failure = null;
        $curl = curl_init($this->endpoint);
        if ($curl === false) throw new RuntimeException('Cannot initialize bank HTTPS transport');
        try {
            $options = [
                CURLOPT_POST => true, CURLOPT_POSTFIELDS => $content,
                CURLOPT_HTTPHEADER => ['Content-Type: text/xml; charset=UTF-8', 'Accept-Encoding: identity', 'Expect:'],
                CURLOPT_FOLLOWLOCATION => false, CURLOPT_MAXREDIRS => 0,
                CURLOPT_PROTOCOLS_STR => 'https', CURLOPT_REDIR_PROTOCOLS_STR => 'https',
                CURLOPT_PROXY => '', CURLOPT_NOPROXY => '*',
                CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2,
                CURLOPT_SSLVERSION => CURL_SSLVERSION_TLSv1_2,
                CURLOPT_CONNECTTIMEOUT_MS => min(5000, $this->timeoutMs), CURLOPT_TIMEOUT_MS => $this->timeoutMs,
                CURLOPT_HTTP_CONTENT_DECODING => false,
                CURLOPT_HEADERFUNCTION => static function ($handle, string $line) use (&$headerBytes, &$failure): int {
                    $headerBytes += strlen($line);
                    if ($headerBytes > self::MAX_HEADER_BYTES) {
                        $failure = 'Bank response headers exceed size limit';
                        return 0;
                    }
                    if (stripos($line, 'Content-Encoding:') === 0 && strtolower(trim(substr($line, 17))) !== 'identity') {
                        $failure = 'Unexpected bank HTTP content encoding';
                        return 0;
                    }
                    return strlen($line);
                },
                CURLOPT_WRITEFUNCTION => static function ($handle, string $chunk) use (&$body, &$failure): int {
                    if (strlen($chunk) > self::MAX_RESPONSE_BYTES - strlen($body)) {
                        $failure = 'Bank response body exceeds size limit';
                        return 0;
                    }
                    $body .= $chunk;
                    return strlen($chunk);
                },
            ];
            if ($this->caBundle !== null) $options[CURLOPT_CAINFO] = $this->caBundle;
            if (!curl_setopt_array($curl, $options)) throw new RuntimeException('Cannot configure bank HTTPS transport');
            $completed = curl_exec($curl);
            if ($failure !== null) throw new RuntimeException($failure);
            if ($completed === false) throw new RuntimeException('Bank HTTPS request failed (curl ' . curl_errno($curl) . ')');
            $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
            if ($status !== 200) throw new RuntimeException('Unexpected bank HTTP status ' . $status);
        } finally {
            // PHP 8.5 releases the CurlHandle when its last reference is dropped.
            unset($curl);
        }
        return self::parseResponse($body);
    }

    public static function parseResponse(string $body): Response
    {
        if ($body === '' || strlen($body) > self::MAX_RESPONSE_BYTES) throw new RuntimeException('Invalid bank XML response size');
        if (!defined('LIBXML_NO_XXE')) throw new RuntimeException('External-entity protection requires libxml 2.13 or later');
        $previous = libxml_use_internal_errors(true);
        $reader = new XMLReader();
        try {
            libxml_clear_errors();
            if (!$reader->XML($body, null, LIBXML_NONET | LIBXML_NO_XXE)) throw new RuntimeException('Invalid bank XML response');
            $reader->setParserProperty(XMLReader::LOADDTD, false);
            $reader->setParserProperty(XMLReader::SUBST_ENTITIES, false);
            $nodes = 0;
            while ($reader->read()) {
                if ($reader->nodeType === XMLReader::DOC_TYPE) throw new RuntimeException('Invalid or prohibited bank XML response');
                if (++$nodes > self::MAX_XML_NODES || $reader->depth > self::MAX_XML_DEPTH
                    || $reader->attributeCount > self::MAX_XML_ATTRIBUTES) {
                    throw new RuntimeException('Bank XML structure exceeds limits');
                }
            }
            if (libxml_get_errors() !== []) throw new RuntimeException('Invalid or prohibited bank XML response');
            $response = new Response();
            $response->resolveExternals = false;
            $response->substituteEntities = false;
            $loaded = $response->loadXML($body, LIBXML_NONET | LIBXML_NO_XXE);
            if (!$loaded || $response->doctype !== null) throw new RuntimeException('Invalid or prohibited bank XML response');
            return $response;
        } finally {
            $reader->close();
            libxml_clear_errors();
            libxml_use_internal_errors($previous);
        }
    }
}
