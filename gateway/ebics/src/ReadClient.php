<?php
declare(strict_types=1);

namespace KT\Banking;

use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\EbicsClient;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\EbicsClientOptions;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\Order\DownloadOrderResult;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Orders\BTD;

// Internal composition boundary, not an authorization layer or configured gateway.
final readonly class ReadClient
{
    private EbicsClient $client;
    private DownloadBudget $transport;

    public static function https(Bank $bank, User $user, Keyring $keyring, ?string $caBundle = null): self
    {
        return new self($bank, $user, $keyring, new HttpsTransport($bank->getUrl(), $caBundle));
    }

    public function __construct(Bank $bank, User $user, Keyring $keyring, HttpClientInterface $http)
    {
        $this->transport = new DownloadBudget($http, $bank->getUrl());
        $options = (new EbicsClientOptions())->setHttpClient($this->transport)->setZipCompressor(new BoundedZlib());
        $this->client = new EbicsClient($bank, $user, $keyring, $options);
    }

    public function executeDownloadOrder(BTD $order): DownloadOrderResult
    {
        $this->transport->begin();
        try {
            return $this->client->executeDownloadOrder($order);
        } finally {
            $this->transport->end();
        }
    }
}
