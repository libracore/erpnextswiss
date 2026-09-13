<?php
declare(strict_types=1);
require __DIR__ . '/../vendor/autoload.php';
require __DIR__ . '/ScriptedBank.php';
require __DIR__ . '/compressed_payload.php';

use KT\Banking\DownloadReceiver;
use KT\Banking\ReadRequest;
use KT\Banking\TransferJournal;

$mounts = file_get_contents('/proc/self/mountinfo');
if (getenv('KT_GATEWAY_SIZE_TEST') !== '1' || posix_geteuid() !== 10001
    || ini_get('memory_limit') !== '256M'
    || !preg_match('~^\d+ \d+ \S+ \S+ /tmp [^\n]* - tmpfs [^\n]*size=131072k(?:,|\s|$)~m', $mounts)) {
    throw new RuntimeException('Explicit isolated 128 MiB tmpfs and 256M PHP size test required');
}
umask(0077);
$path = '/tmp/kt-full-size-' . bin2hex(random_bytes(8));
mkdir($path, 0700);
TransferJournal::initialize($path, 'test-key', str_repeat('K', 32));
$journal = new TransferJournal($path, 'test-key', str_repeat('K', 32));
$request = new ReadRequest('site', 'connection', 'participant', 'full-size',
    'camt.053.001.08', '2026-09-01', '2026-09-02');
$bank = new ScriptedBank('');
$bank->compressedPayload = compressed_repeat(TransferJournal::MAX_BYTES);
$bank->onReceipt = static function () use ($path, $request): void {
    $reopened = new TransferJournal($path, 'test-key', str_repeat('K', 32));
    $row = $reopened->find($request);
    if ($row['payload_bytes'] !== TransferJournal::MAX_BYTES || $row['receipt_state'] !== 'unconfirmed') {
        throw new RuntimeException('Full-size original not durable before receipt');
    }
};
$receiver = new DownloadReceiver($journal);
$result = $receiver->receive($bank->client, $request);
$bytes = $journal->payload($request);
if ($result['receipt_state'] !== 'confirmed' || $bank->receipts !== 1
    || strlen($bytes) !== TransferJournal::MAX_BYTES || strspn($bytes, 'X') !== strlen($bytes)) {
    throw new RuntimeException('Full-size original or receipt changed');
}
unset($bytes);
$phases = count($bank->phases);
if (!$receiver->receive($bank->client, $request)['replayed'] || count($bank->phases) !== $phases) {
    throw new RuntimeException('Full-size replay contacted bank');
}
echo 'PASS full-size original persistence, readback, receipt and local replay '
    . json_encode(['bytes' => TransferJournal::MAX_BYTES, 'peak_bytes' => memory_get_peak_usage(true),
        'network' => 'scripted-http-only'], JSON_THROW_ON_ERROR) . "\n";
