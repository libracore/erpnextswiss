<?php
declare(strict_types=1);
require __DIR__ . '/../vendor/autoload.php';
require __DIR__ . '/ScriptedBank.php';

use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;
use EbicsApi\Ebics\Services\HttpClient;
use KT\Banking\DownloadReceiver;
use KT\Banking\HttpsTransport;
use KT\Banking\ReadRequest;
use KT\Banking\TransferJournal;

if (getenv('KT_GATEWAY_HTTPS_TEST') !== '1' || posix_geteuid() !== 10001) exit(2);
umask(0077);
$checks = 0;
function check(bool $ok, string $message): void {
    global $checks;
    $checks++;
    if (!$ok) throw new RuntimeException($message);
}
function rejects(callable $operation, string $message): void {
    try { $operation(); } catch (RuntimeException | InvalidArgumentException $error) {
        check(str_contains($error->getMessage(), $message), 'Wrong failure: ' . $error->getMessage());
        check(!str_contains($error->getMessage(), 'private-server-body'), 'No response body leaked');
        return;
    }
    throw new RuntimeException('Expected failure: ' . $message);
}
$directory = '/tmp/kt-https-' . bin2hex(random_bytes(8));
mkdir($directory, 0700);
$key = openssl_pkey_new(['private_key_type' => OPENSSL_KEYTYPE_RSA, 'private_key_bits' => 2048]);
$csr = openssl_csr_new(['commonName' => 'localhost'], $key, ['digest_alg' => 'sha256']);
$cert = openssl_csr_sign($csr, null, $key, 1, ['digest_alg' => 'sha256']);
if (!openssl_pkey_export($key, $keyPem) || !openssl_x509_export($cert, $certPem)) throw new RuntimeException('Synthetic TLS setup failed');
file_put_contents($directory . '/key.pem', $keyPem);
file_put_contents($directory . '/cert.pem', $certPem);
file_put_contents($directory . '/sentinel', 'synthetic-xml-file-marker');

$xxe = '<!DOCTYPE response [<!ENTITY sample SYSTEM "file://' . $directory . '/sentinel">]><response>&sample;</response>';
$baseline = new class($xxe) extends HttpClient {
    public function __construct(private string $body) {}
    public function post(string $url, Request $request): Response { return $this->createResponse($this->body); }
};
$request = new Request();
$request->loadXML('<request>synthetic</request>');
check($baseline->post('', $request)->documentElement->textContent === 'synthetic-xml-file-marker', 'Native SDK local entity expansion reproduced with synthetic file');
$loads = 0;
$loader = libxml_get_external_entity_loader();
libxml_set_external_entity_loader(static function () use (&$loads) { $loads++; return null; });
try {
    foreach ([$xxe, '<!DOCTYPE response SYSTEM "https://bank.invalid/external"><response/>',
        '<!DOCTYPE response [<!ENTITY x "inline">]><response>&x;</response>',
        iconv('UTF-8', 'UTF-16', '<?xml version="1.0" encoding="UTF-16"?>' . $xxe)] as $xml) {
        rejects(fn() => HttpsTransport::parseResponse($xml), 'Invalid or prohibited bank XML');
    }
    check($loads === 0, 'Protected parser never invoked an external entity loader');
} finally { libxml_set_external_entity_loader($loader); }
foreach (['', '<private-server-body'] as $xml) rejects(fn() => HttpsTransport::parseResponse($xml), 'bank XML');
check(HttpsTransport::parseResponse('<r>a &amp; b</r>')->documentElement->textContent === 'a & b', 'Normal XML escapes remain valid');
foreach (['<r>' . str_repeat('<a/>', HttpsTransport::MAX_XML_NODES) . '</r>',
    str_repeat('<a>', HttpsTransport::MAX_XML_DEPTH + 2) . str_repeat('</a>', HttpsTransport::MAX_XML_DEPTH + 2),
    '<r ' . implode(' ', array_map(fn($n) => 'a' . $n . '="x"', range(0, HttpsTransport::MAX_XML_ATTRIBUTES))) . '/>'] as $xml) {
    rejects(fn() => HttpsTransport::parseResponse($xml), 'XML structure exceeds limits');
}
check(HttpsTransport::parseResponse('<r>' . str_repeat('<a/>', HttpsTransport::MAX_XML_NODES - 2) . '</r>')
    ->documentElement->childNodes->length === HttpsTransport::MAX_XML_NODES - 2, 'Exact XML node boundary accepted');
check(libxml_use_internal_errors() === false, 'Parser restores caller error mode');

foreach (['http://localhost/ebics', 'file:///tmp/file', 'https://user:pass@localhost/ebics',
    'https://localhost/ebics?key=secret', 'https://localhost/ebics#fragment', "https://localhost/ebi\ncs"] as $url) {
    rejects(fn() => new HttpsTransport($url), 'Invalid configured bank HTTPS');
}
foreach ([0, 99, 30001] as $timeout) rejects(fn() => new HttpsTransport('https://localhost/ebics', timeoutMs: $timeout), 'Invalid configured bank HTTPS');
rejects(fn() => new HttpsTransport('https://localhost/ebics', '/absent-ca'), 'CA bundle is unavailable');

// Prepare signed responses through the existing real-SDK fixture; the later
// receipt run uses actual verified TLS/cURL and a separate empty journal.
$bank = new ScriptedBank("PK\x03\x04 signed HTTPS original\x00\xff");
$req = new ReadRequest('site', 'connection', 'participant', 'https', 'camt.053.001.08', '2026-09-01', '2026-09-02');
mkdir($directory . '/prepare', 0700);
TransferJournal::initialize($directory . '/prepare', 'test-key', str_repeat('K', 32));
(new DownloadReceiver(new TransferJournal($directory . '/prepare', 'test-key', str_repeat('K', 32))))->receive($bank->client, $req);
foreach ($bank->responses as $index => $xml) file_put_contents($directory . '/bank-' . ($index + 1) . '.xml', $xml);
$process = proc_open([PHP_BINARY, __DIR__ . '/tls_server.php', $directory],
    [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
if (!is_resource($process)) throw new RuntimeException('Cannot start isolated server');
fclose($pipes[0]);
try {
    stream_set_timeout($pipes[1], 5);
    $address = trim(fgets($pipes[1]) ?: '');
    check((bool)preg_match('/\A127\.0\.0\.1:[0-9]+\z/', $address), 'Server listens on loopback only');
    $base = 'https://localhost:' . explode(':', $address)[1];
    $ca = $directory . '/cert.pem';
    $normal = new HttpsTransport($base . '/normal', $ca);
    rejects(fn() => $normal->post($base . '/other', $request), 'differs from trusted binding');
    $oversizeRequest = new Request();
    $oversizeRequest->loadXML('<r>' . str_repeat('X', HttpsTransport::MAX_REQUEST_BYTES) . '</r>');
    rejects(fn() => $normal->post($base . '/normal', $oversizeRequest), 'request exceeds size');
    unset($oversizeRequest);
    check(!file_exists($directory . '/requests.log'), 'Binding/size validation precedes any HTTP request');
    check($normal->post($base . '/normal', $request)->documentElement->textContent === 'safe & exact', 'Real TLS POST with trusted certificate');
    $environment = [];
    foreach (['https_proxy', 'HTTPS_PROXY', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy'] as $name) {
        $environment[$name] = getenv($name);
        putenv($name . '=' . (strtolower($name) === 'no_proxy' ? '' : 'http://127.0.0.1:1'));
    }
    try {
        check($normal->post($base . '/normal', $request)->documentElement->textContent === 'safe & exact', 'Environment proxies cannot reroute bank traffic');
    } finally {
        foreach ($environment as $name => $value) putenv($value === false ? $name : $name . '=' . $value);
    }
    rejects(fn() => (new HttpsTransport($base . '/normal'))->post($base . '/normal', $request), 'HTTPS request failed');
    $wrongHost = 'https://' . $address . '/normal';
    rejects(fn() => (new HttpsTransport($wrongHost, $ca))->post($wrongHost, $request), 'HTTPS request failed');
    foreach (['oversized' => 'body exceeds size', 'chunked' => 'body exceeds size', 'headers' => 'headers exceed size',
        'redirect' => 'HTTP status 302', 'encoded' => 'content encoding', 'empty' => 'XML response size',
        'malformed' => 'prohibited bank XML', 'error' => 'HTTP status 500'] as $path => $message) {
        rejects(fn() => (new HttpsTransport($base . '/' . $path, $ca))->post($base . '/' . $path, $request), $message);
    }
    $exact = (new HttpsTransport($base . '/exact', $ca))->post($base . '/exact', $request);
    check(strlen($exact->documentElement->textContent) === HttpsTransport::MAX_RESPONSE_BYTES - 7, 'Exact HTTP body limit accepted without truncation');
    unset($exact);
    $start = hrtime(true);
    rejects(fn() => (new HttpsTransport($base . '/slow', $ca, 200))->post($base . '/slow', $request), 'HTTPS request failed');
    check((hrtime(true) - $start) / 1e9 < 2, 'Configured request timeout bounds elapsed time');
    check($normal->post($base . '/normal', $request)->documentElement->textContent === 'safe & exact', 'Transport recovers after failures');
    $calls = file($directory . '/requests.log', FILE_IGNORE_NEW_LINES);
    check(!in_array('/target', $calls, true), 'Redirect not followed');
    foreach (['/oversized', '/chunked', '/headers', '/redirect', '/error', '/slow'] as $path) {
        check(count(array_filter($calls, fn($call) => $call === $path)) === 1, 'No implicit retry for ' . $path);
    }
    mkdir($directory . '/receive', 0700);
    TransferJournal::initialize($directory . '/receive', 'test-key', str_repeat('K', 32));
    $journal = new TransferJournal($directory . '/receive', 'test-key', str_repeat('K', 32));
    $receiver = new DownloadReceiver($journal);
    $client = $bank->httpsClient($base . '/bank', $ca);
    $result = $receiver->receive($client, $req);
    check($result['receipt_state'] === 'confirmed', 'Real signed SDK transfer through bounded verified HTTPS');
    check($journal->payload($req) === "PK\x03\x04 signed HTTPS original\x00\xff", 'HTTPS original byte-exact');
    check($receiver->receive($client, $req)['replayed'], 'HTTPS transfer locally replayed');
    $calls = file($directory . '/requests.log', FILE_IGNORE_NEW_LINES);
    check(count(array_filter($calls, fn($call) => $call === '/bank')) === 3, 'Two actual HTTPS segments and one receipt, no replay traffic');
    echo json_encode(['assertions' => $checks, 'network' => 'verified-tls-loopback-only'], JSON_THROW_ON_ERROR) . "\n";
} finally {
    proc_terminate($process);
    fclose($pipes[1]);
    $errors = stream_get_contents($pipes[2]);
    fclose($pipes[2]);
    proc_close($process);
    if ($errors !== '') throw new RuntimeException('TLS fixture diagnostics: ' . $errors);
}
