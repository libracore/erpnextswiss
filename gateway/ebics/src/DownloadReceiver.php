<?php
declare(strict_types=1);

namespace KT\Banking;

use EbicsApi\Ebics\Contracts\DownloadTransactionInterface;
use EbicsApi\Ebics\Contracts\EbicsClientInterface;
use EbicsApi\Ebics\Contexts\BTDContext;
use EbicsApi\Ebics\Contexts\RequestContext;
use EbicsApi\Ebics\Orders\BTD;
use RuntimeException;

final readonly class DownloadReceiver
{
    public function __construct(private TransferJournal $journal) {}

    public function order(ReadRequest $request): BTD
    {
        $profile = (new BTDContext())
            ->setServiceName($request->profile === 'camt.053.001.08' ? 'EOP' : 'REP')
            ->setScope('CH')->setContainerType('ZIP')
            ->setMsgName(substr($request->profile, 0, 8))->setMsgNameVersion('08')
            ->setParserFormat(EbicsClientInterface::FILE_PARSER_FORMAT_TEXT);
        $context = (new RequestContext())->setAckClosure(function (DownloadTransactionInterface $transfer) use ($request): bool {
            $this->journal->persist($request, $transfer->getId() ?? '', $transfer->getNumSegments(), $transfer->getOrderData());
            return true;
        });
        return new BTD($profile, ReadRequest::date($request->from), ReadRequest::date($request->until), $context);
    }

    public function receive(EbicsClientInterface $client, ReadRequest $request): array
    {
        return $this->journal->exclusive($request, function () use ($client, $request): array {
            $existing = $this->journal->find($request);
            if ($existing) return [...$existing, 'replayed' => true];
            $result = $client->executeDownloadOrder($this->order($request));
            $transfer = $result->getTransaction();
            if (!$transfer instanceof DownloadTransactionInterface) throw new RuntimeException('Expected completed download transaction');
            $stored = $this->journal->confirm($request, $transfer->getId() ?? '', $transfer->getReceipt()->getContent());
            return [...$stored, 'replayed' => false];
        });
    }
}
