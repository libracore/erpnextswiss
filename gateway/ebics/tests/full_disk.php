<?php
declare(strict_types=1);
require __DIR__ . '/../vendor/autoload.php';
require __DIR__ . '/ScriptedBank.php';

use KT\Banking\DownloadReceiver;
use KT\Banking\ReadRequest;
use KT\Banking\TransferJournal;

// Never fill a caller-supplied directory or host filesystem. The dedicated mount is mandatory.
$path = '/kt-disk-full';
$mounts = file_get_contents('/proc/self/mountinfo');
if (getenv('KT_GATEWAY_DISK_FULL_TEST') !== '1' || posix_geteuid() !== 10001
    || !preg_match('~^\d+ \d+ \S+ \S+ /kt-disk-full [^\n]* - tmpfs [^\n]*size=1024k(?:,|\s|$)~m', $mounts)) {
    throw new RuntimeException('Only explicit isolated 1 MiB tmpfs /kt-disk-full is permitted');
}
umask(0077);
TransferJournal::initialize($path, 'test-key', str_repeat('K', 32));
$journal = new TransferJournal($path, 'test-key', str_repeat('K', 32));
$request = new ReadRequest('site', 'connection', 'participant', 'disk-full', 'camt.053.001.08', '2026-09-01', '2026-09-02');
$filler = fopen($path . '/test-filler', 'x');
if (!$filler) throw new RuntimeException('Cannot create isolated test filler');
try {
    $written = 0;
    while ($written < 2 * 1024 * 1024 && ($count = @fwrite($filler, str_repeat('x', 65536))) > 0) $written += $count;
    fclose($filler);
    if ($written >= 2 * 1024 * 1024) throw new RuntimeException('Expected bounded tmpfs was not exhausted');
    $bank = new ScriptedBank(str_repeat('bank original for disk-full test ', 2000));
    $receiver = new DownloadReceiver($journal);
    try {
        $receiver->receive($bank->client, $request);
        throw new RuntimeException('Full disk unexpectedly accepted transfer');
    } catch (PDOException $error) {
        if (($error->errorInfo[1] ?? null) !== 13) throw $error;
    }
    if ($bank->receipts !== 0 || count($bank->phases) !== 2) throw new RuntimeException('Full disk did not stop receipt after download');
    unlink($path . '/test-filler');
    if ($journal->find($request) !== null) throw new RuntimeException('Partial original survived failed transaction');
    $result = $receiver->receive($bank->client, $request);
    if ($result['receipt_state'] !== 'confirmed' || $bank->receipts !== 1) throw new RuntimeException('Retry after freeing space failed');
    if ($journal->payload($request) !== str_repeat('bank original for disk-full test ', 2000)) throw new RuntimeException('Recovered bytes differ');
    echo "PASS real SQLITE_FULL before acknowledgement, no partial row, recovery and exact original\n";
} finally {
    if (is_resource($filler)) fclose($filler);
    if (is_file($path . '/test-filler')) unlink($path . '/test-filler');
}
