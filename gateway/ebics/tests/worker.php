<?php
declare(strict_types=1);
require __DIR__ . '/../vendor/autoload.php';

use KT\Banking\ReadRequest;
use KT\Banking\TransferJournal;
use KT\Banking\DownloadReceiver;

$request = new ReadRequest('site', 'connection', 'participant', 'restart', 'camt.053.001.08', '2026-09-01', '2026-09-02');
$journal = new TransferJournal($argv[2], 'test-key', str_repeat('K', 32));
if ($argv[1] === 'receipt-crash') {
    require __DIR__ . '/ScriptedBank.php';
    $bank = new ScriptedBank('original before hard process termination');
    $bank->onReceipt = static function (): void {
        echo 'committed-before-kill';
        flush();
        posix_kill(getmypid(), 9);
        throw new RuntimeException('Expected test process termination');
    };
    (new DownloadReceiver($journal))->receive($bank->client, $request);
    throw new RuntimeException('Unexpected return from terminated test');
}
if ($argv[1] === 'persist') {
    $journal->persist($request, 'TESTRESTART', 1, 'restart original');
    exit(0);
}
if ($argv[1] === 'read') {
    echo $journal->payload($request);
    exit(0);
}
if ($argv[1] === 'lock') {
    try {
        $journal->exclusive($request, static fn() => print('acquired'));
        exit(0);
    } catch (RuntimeException $error) {
        if ($error->getMessage() !== 'Participant transport is already running') throw $error;
        echo 'blocked';
        exit(23);
    }
}
throw new RuntimeException('Unknown test worker operation');
