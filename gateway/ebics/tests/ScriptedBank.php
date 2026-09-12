<?php
declare(strict_types=1);

use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\EbicsClient;
use EbicsApi\Ebics\Factories\Crypt\RSAFactory;
use EbicsApi\Ebics\Factories\SignatureFactory;
use EbicsApi\Ebics\Handlers\AuthSignatureHandlerV30;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\EbicsClientOptions;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Models\X509\BankX509Generator;
use EbicsApi\Ebics\Services\CryptService;
use EbicsApi\Ebics\Services\Processor\AESEncryptor;
use EbicsApi\Ebics\Services\Processor\Base64Encoder;
use EbicsApi\Ebics\Services\RandomService;
use EbicsApi\Ebics\Services\TransactionKeyResolver;

// Test-only HTTP replacement. Real SDK signing, encryption, segment handling and receipt flow;
// synthetic keys exist only in memory. There is no HTTP/network fallback.
final class ScriptedBank implements HttpClientInterface
{
    private static ?Keyring $keys = null;
    public EbicsClient $client;
    public array $phases = [];
    public array $requests = [];
    public int $receipts = 0;
    public string $mode = 'normal';
    public ?Closure $onReceipt = null;
    public int $segments = 2;
    private array $parts = [];
    private string $encryptedKey;
    private AuthSignatureHandlerV30 $signer;
    private AESEncryptor $aes;

    public function __construct(private string $payload)
    {
        $keys = self::$keys ?? new Keyring(Keyring::VERSION_30);
        $keys->setPassword('ephemeral-offline-test-password');
        $options = (new EbicsClientOptions())->setHttpClient($this);
        $this->client = new EbicsClient(new Bank('TESTBANK', 'https://bank.invalid/ebics'), new User('TEST', 'TEST'), $keys, $options);
        $this->aes = new AESEncryptor(new TransactionKeyResolver());
        $rsa = new RSAFactory($this->aes);
        if (self::$keys === null) {
            $generator = new BankX509Generator();
            $generator->setCertificateOptionsByBank($this->client->getBank());
            $keys->setCertificateGenerator($generator);
            $this->client->createUserSignatures();
            $factory = new SignatureFactory($rsa);
            $keys->setBankSignatureX($factory->createSignatureX($keys->getUserSignatureX()->getPublicKey()));
            $keys->setBankSignatureE($factory->createSignatureE($keys->getUserSignatureE()->getPublicKey()));
            $keys->getBankSignatureX()->setCertificateContent($keys->getUserSignatureX()->getCertificateContent());
            $keys->getBankSignatureE()->setCertificateContent($keys->getUserSignatureE()->getCertificateContent());
            self::$keys = $keys;
        }
        $encoder = new Base64Encoder();
        $this->signer = new AuthSignatureHandlerV30($encoder, $keys, new CryptService($rsa, $this->aes, new RandomService(), $encoder));
    }

    public function post(string $url, Request $request): Response
    {
        if ($url !== 'https://bank.invalid/ebics') throw new RuntimeException('Unexpected destination in offline test');
        $phase = $request->getElementsByTagName('TransactionPhase')->item(0)?->textContent;
        $this->phases[] = $phase;
        $this->requests[] = $request->getContent();
        if ($phase === 'Receipt') {
            $this->receipts++;
            if ($request->getElementsByTagName('ReceiptCode')->item(0)?->textContent !== '0') {
                throw new RuntimeException('Expected positive receipt in successful test path');
            }
            if ($this->onReceipt) ($this->onReceipt)();
            if ($this->mode === 'receipt_timeout') throw new RuntimeException('Synthetic receipt response timeout');
            return $this->response('Receipt', 1, '', '', $this->mode === 'receipt_error' ? '091002' : '000000');
        }
        if ($phase === 'Initialisation' || $phase === 'Initialization') {
            if ($request->getElementsByTagName('AdminOrderType')->item(0)?->textContent !== 'BTD') {
                throw new RuntimeException('Only BTD downloads are allowed by the test bank');
            }
            $key = random_bytes(16);
            if (!openssl_public_encrypt($key, $encryptedKey, self::$keys->getUserSignatureE()->getPublicKey()->getKey(), OPENSSL_PKCS1_PADDING)) {
                throw new RuntimeException('Cannot encrypt synthetic transaction key');
            }
            $this->encryptedKey = base64_encode($encryptedKey);
            $encoded = base64_encode($this->aes->encrypt(gzcompress($this->payload), ['transactionKey' => $key]));
            $this->parts = str_split($encoded, (int)ceil(strlen($encoded) / $this->segments));
            return $this->response('Initialisation', 1, $this->parts[0], $this->encryptedKey);
        }
        if ($phase === 'Transfer') {
            $number = (int)$request->getElementsByTagName('SegmentNumber')->item(0)?->textContent;
            if (!isset($this->parts[$number - 1])) throw new RuntimeException('Unexpected segment requested');
            return $this->response('Transfer', $number, $this->parts[$number - 1], $this->encryptedKey);
        }
        throw new RuntimeException('Unexpected EBICS phase; initialization/upload must not occur');
    }

    private function response(string $phase, int $number, string $data, string $key, string $code = '000000'): Response
    {
        $response = new Response();
        $response->loadXML('<ebicsResponse xmlns="urn:org:ebics:H005" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Version="H005" Revision="1">'
            . '<header authenticate="true"><static><TransactionID>TESTTRANSACTION01</TransactionID><NumSegments>' . count($this->parts) . '</NumSegments></static>'
            . '<mutable><TransactionPhase>' . $phase . '</TransactionPhase><SegmentNumber lastSegment="true">' . $number . '</SegmentNumber>'
            . '<ReturnCode>000000</ReturnCode><ReportText>Offline test</ReportText></mutable></header>'
            . '<body><DataTransfer><DataEncryptionInfo authenticate="true"><TransactionKey>' . $key . '</TransactionKey></DataEncryptionInfo>'
            . '<OrderData>' . $data . '</OrderData></DataTransfer><ReturnCode authenticate="true">' . $code . '</ReturnCode></body></ebicsResponse>');
        $this->signer->handle($response);
        if ($this->mode === 'invalid_signature') {
            $response->getElementsByTagName('TransactionID')->item(0)->nodeValue = 'TAMPERED';
        }
        return $response;
    }
}
