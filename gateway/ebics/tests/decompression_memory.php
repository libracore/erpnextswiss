<?php
declare(strict_types=1);
require __DIR__ . '/../vendor/autoload.php';
require __DIR__ . '/compressed_payload.php';

use EbicsApi\Ebics\Services\Processor\ZipCompressor;
use KT\Banking\BoundedZlib;
use KT\Banking\TransferJournal;

if (ini_get('memory_limit') !== '96M' || !in_array($argv[1] ?? '', ['baseline', 'bounded'], true)) {
    throw new RuntimeException('Explicit 96M isolated decompression test required');
}
$payload = compressed_repeat(268435456);
if ($argv[1] === 'baseline') {
    // The control must reach native decompression, not fail while making test data.
    echo 'before-baseline-decode';
    flush();
    (new ZipCompressor())->uncompress($payload);
    throw new RuntimeException('Unbounded baseline unexpectedly returned');
}
$pipe = new BoundedZlib();
try {
    $pipe->uncompress($payload);
    throw new RuntimeException('Oversized payload unexpectedly returned');
} catch (RuntimeException $error) {
    if ($error->getMessage() !== 'Invalid or oversized zlib payload') throw $error;
}
if ($pipe->uncompress(gzcompress('valid after rejection')) !== 'valid after rejection') {
    throw new RuntimeException('Decoder unusable after rejection');
}
$exact = $pipe->uncompress(compressed_repeat(TransferJournal::MAX_BYTES));
if (strlen($exact) !== TransferJournal::MAX_BYTES || strspn($exact, 'X') !== TransferJournal::MAX_BYTES) {
    throw new RuntimeException('Exact output boundary changed or truncated');
}
echo json_encode(['bounded' => true, 'exact_limit' => strlen($exact),
    'peak_bytes' => memory_get_peak_usage(true)], JSON_THROW_ON_ERROR);
