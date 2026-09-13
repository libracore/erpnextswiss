<?php
declare(strict_types=1);
require __DIR__ . '/../vendor/autoload.php';
require __DIR__ . '/ScriptedBank.php';

use KT\Banking\DownloadReceiver;
use KT\Banking\ReadRequest;
use KT\Banking\TransferJournal;

if (getenv('KT_GATEWAY_EXPORT_TEST') !== '1') throw new RuntimeException('Isolated CI export only');
umask(0077);
$payload = stream_get_contents(STDIN, TransferJournal::MAX_BYTES + 1);
if ($payload === false || strlen($payload) < 1 || strlen($payload) > TransferJournal::MAX_BYTES) {
    throw new RuntimeException('Bounded synthetic original required');
}
$path = sys_get_temp_dir() . '/kt-export-' . bin2hex(random_bytes(8));
mkdir($path, 0700);
TransferJournal::initialize($path, 'ci-key', str_repeat('K', 32));
$journal = new TransferJournal($path, 'ci-key', str_repeat('K', 32));
$request = new ReadRequest('ci-site', 'ci-connection', 'ci-participant', 'ci-request',
    'camt.053.001.08', '2026-09-01', '2026-09-12');
$bank = new ScriptedBank($payload);
(new DownloadReceiver($journal))->receive($bank->client, $request);
$before = $journal->find($request);
$handover = $journal->handover($request);
if ($handover['payload'] !== $payload || $journal->find($request) !== $before || count($bank->phases) !== 3) {
    throw new RuntimeException('Preparing handover changed original, journal state or contacted the bank');
}
// Base64 is only the subprocess test bridge, not a deployed HTTP protocol.
echo json_encode(['metadata' => $handover['metadata'], 'payload_base64' => base64_encode($handover['payload'])], JSON_THROW_ON_ERROR);
