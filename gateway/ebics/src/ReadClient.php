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

    public function __construct(Bank $bank, User $user, Keyring $keyring, HttpClientInterface $http)
    {
        $options = (new EbicsClientOptions())->setHttpClient($http)->setZipCompressor(new BoundedZlib());
        $this->client = new EbicsClient($bank, $user, $keyring, $options);
    }

    public function executeDownloadOrder(BTD $order): DownloadOrderResult
    {
        return $this->client->executeDownloadOrder($order);
    }
}
