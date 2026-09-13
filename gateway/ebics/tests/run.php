<?php
declare(strict_types=1);
require __DIR__ . '/../vendor/autoload.php';
require __DIR__ . '/ScriptedBank.php';
require __DIR__ . '/compressed_payload.php';

use KT\Banking\DownloadReceiver;
use KT\Banking\ReadRequest;
use KT\Banking\TransferJournal;
use KT\Banking\BoundedZlib;
use KT\Banking\ReadClient;
use KT\Banking\DownloadBudget;

error_reporting(E_ALL);
set_error_handler(static function (int $severity, string $message, string $file, int $line): bool {
    if (!(error_reporting() & $severity)) return false;
    throw new ErrorException($message, 0, $severity, $file, $line);
});
umask(0077);
$assertions = 0;
$failures = 0;
$root = sys_get_temp_dir() . '/kt-bank-tests-' . bin2hex(random_bytes(8));
mkdir($root, 0700);

function check(bool $condition, string $message): void
{
    global $assertions;
    $assertions++;
    if (!$condition) throw new RuntimeException($message);
}
function rejects(callable $work, string $message, ?string $contains = null): void
{
    try { $work(); } catch (Throwable $error) {
        check($contains === null || str_contains($error->getMessage(), $contains), $message . ': wrong failure: ' . $error->getMessage());
        return;
    }
    check(false, $message . ': did not reject');
}
function request(array $change = []): ReadRequest
{
    return new ReadRequest(...array_replace(['site' => 'site', 'connection' => 'connection', 'participant' => 'participant',
        'request' => 'request', 'profile' => 'camt.053.001.08', 'from' => '2026-09-01', 'until' => '2026-09-02'], $change));
}
function journal(): array
{
    global $root;
    $path = $root . '/' . bin2hex(random_bytes(8));
    mkdir($path, 0700);
    TransferJournal::initialize($path, 'test-key', str_repeat('K', 32));
    return [$path, new TransferJournal($path, 'test-key', str_repeat('K', 32))];
}
function worker(string $mode, string $path): array
{
    $process = proc_open([PHP_BINARY, __DIR__ . '/worker.php', $mode, $path], [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
    if (!is_resource($process)) throw new RuntimeException('Worker cannot start');
    fclose($pipes[0]);
    $output = stream_get_contents($pipes[1]);
    $errors = stream_get_contents($pipes[2]);
    fclose($pipes[1]); fclose($pipes[2]);
    $code = proc_close($process);
    check($errors === '', 'No worker diagnostics: ' . $errors);
    return [$code, $output];
}
function test(string $name, callable $work): void
{
    global $failures;
    try { $work(); echo "PASS $name\n"; }
    catch (Throwable $error) { $failures++; echo "FAIL $name: " . $error::class . ': ' . $error->getMessage() . "\n" . $error->getTraceAsString() . "\n"; }
}

test('reviewed dependency reference', function (): void {
    check(Composer\InstalledVersions::getReference('ebics-api/ebics-client-php') === 'c0cd3d448fa01ea0442e72b2720be0d371070c12', 'Reviewed SDK commit, not mutable version label');
});

test('bounded native zlib validates input and preserves binary output', function (): void {
    $pipe = new BoundedZlib();
    $bytes = "PK\x03\x04\x00\xff" . random_bytes(2048);
    check($pipe->uncompress(gzcompress($bytes)) === $bytes, 'Binary inner container preserved');
    check(gzuncompress($pipe->compress($bytes)) === $bytes, 'SDK compression contract preserved');
    check($pipe->uncompress(gzcompress('')) === '', 'Valid empty stream decoded; journal still rejects empty originals');
    foreach (['', 'x', str_repeat('x', BoundedZlib::MAX_COMPRESSED_BYTES + 1)] as $invalid) {
        rejects(fn() => $pipe->uncompress($invalid), 'Input byte boundary', 'Invalid compressed payload size');
    }
    $damaged = gzcompress($bytes);
    $damaged[-1] = chr(ord($damaged[-1]) ^ 1);
    foreach (['not a stream', gzencode($bytes), gzdeflate($bytes), substr(gzcompress($bytes), 0, -1),
        $damaged, str_repeat('x', BoundedZlib::MAX_COMPRESSED_BYTES)] as $invalid) {
        rejects(fn() => $pipe->uncompress($invalid), 'Malformed zlib fails closed', 'Invalid or oversized zlib payload');
    }
    foreach ([TransferJournal::MAX_BYTES + 1, TransferJournal::MAX_BYTES + 3 * 1048576] as $size) {
        rejects(fn() => $pipe->uncompress(compressed_repeat($size)), 'Native growth buffer cannot bypass exact limit', 'Invalid or oversized zlib payload');
    }
    check($pipe->uncompress(gzcompress($bytes)) === $bytes, 'Decoder recovers after invalid inputs');
});

test('real memory limit distinguishes unbounded SDK from bounded exact-size decoding', function (): void {
    foreach (['baseline', 'bounded'] as $mode) {
        $process = proc_open([PHP_BINARY, '-d', 'memory_limit=96M', '-d', 'display_errors=stderr',
            '-d', 'log_errors=0', __DIR__ . '/decompression_memory.php', $mode],
            [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
        if (!is_resource($process)) throw new RuntimeException('Cannot start memory-limit worker');
        fclose($pipes[0]);
        $output = stream_get_contents($pipes[1]);
        $errors = stream_get_contents($pipes[2]);
        fclose($pipes[1]); fclose($pipes[2]);
        $code = proc_close($process);
        if ($mode === 'baseline') {
            check($code !== 0 && $output === 'before-baseline-decode', 'Baseline failed during actual SDK decode');
            check(str_contains($errors, 'Allowed memory size'), 'Baseline native memory exhaustion reproduced');
        } else {
            check($code === 0 && $errors === '', 'Bounded worker succeeds under same limit: ' . $errors);
            $result = json_decode($output, true, flags: JSON_THROW_ON_ERROR);
            check($result['bounded'] && $result['exact_limit'] === TransferJournal::MAX_BYTES, 'Oversized rejected and exact limit retained');
            check($result['peak_bytes'] < 96 * 1048576, 'Actual peak stays within memory bound');
            echo 'MEMORY ' . $output . "\n";
        }
    }
});

test('receiver requires the constrained SDK composition', function (): void {
    $type = (new ReflectionMethod(DownloadReceiver::class, 'receive'))->getParameters()[0]->getType();
    check($type->getName() === ReadClient::class, 'An arbitrary unbounded SDK cannot enter receive');
    foreach (['executeUploadOrder', 'executeInitializationOrder', 'createUserSignatures'] as $method) {
        check(!method_exists(ReadClient::class, $method), 'Read client does not expose ' . $method);
    }
});

test('download-wide request, byte, endpoint and elapsed-time budgets', function (): void {
    $inner = new class implements EbicsApi\Ebics\Contracts\HttpClientInterface {
        public int $calls = 0;
        public string $xml = '<r/>';
        public ?Closure $onPost = null;
        public function post(string $url, EbicsApi\Ebics\Models\Http\Request $request): EbicsApi\Ebics\Models\Http\Response {
            $this->calls++;
            if ($this->onPost) ($this->onPost)();
            $response = new EbicsApi\Ebics\Models\Http\Response();
            $response->loadXML($this->xml);
            return $response;
        }
    };
    $now = 0.0;
    $budget = new DownloadBudget($inner, 'https://bank.invalid/ebics', static function () use (&$now): float { return $now; });
    $req = new EbicsApi\Ebics\Models\Http\Request();
    $post = fn() => $budget->post('https://bank.invalid/ebics', $req);
    rejects($post, 'Inactive transport cannot request', 'scope is inactive');
    $budget->begin();
    rejects(fn() => $budget->begin(), 'No overlapping use', 'already active');
    rejects(fn() => $budget->post('https://other.invalid/ebics', $req), 'No changed endpoint', 'scope is inactive');
    check($inner->calls === 0, 'Invalid scope rejected before delegate');
    for ($i = 0; $i < DownloadBudget::MAX_SEGMENTS + 1; $i++) $post();
    rejects($post, 'Bound actual exchanges', 'request or time budget');
    check($inner->calls === DownloadBudget::MAX_SEGMENTS + 1, 'No excess delegate call');
    $budget->end();
    $budget->begin();
    $now = DownloadBudget::MAX_SECONDS;
    $before = $inner->calls;
    rejects($post, 'Deadline enforced before delegate', 'request or time budget');
    check($inner->calls === $before, 'Expired deadline has no network side effect');
    $budget->end();
    $budget->begin();
    $inner->onPost = static function () use (&$now): void { $now += DownloadBudget::MAX_SECONDS; };
    rejects($post, 'Late response rejected', 'response or time budget');
    $inner->onPost = null;
    $budget->end();
    $budget->begin();
    $inner->xml = '<r>' . str_repeat('X', 1048576) . '</r>';
    for ($i = 0; $i < 19; $i++) $post();
    rejects($post, 'Small responses cannot bypass total bytes', 'response or time budget');
    $budget->end();
    foreach (['65', '10000', '-1', 'n/a'] as $count) {
        $budget->begin();
        $inner->xml = '<r><NumSegments>' . $count . '</NumSegments></r>';
        rejects($post, 'Invalid declared segment count', 'segment count exceeds');
        $budget->end();
    }
    $budget->begin();
    $inner->xml = '<r xmlns:h="urn:org:ebics:H005"><h:NumSegments> 00064 </h:NumSegments></r>';
    check(trim($post()->documentElement->textContent) === '00064', 'Exact segment limit with XML integer whitespace/prefix accepted');
    $budget->end();
    $budget->begin();
    $inner->xml = '<r xmlns:h="urn:org:ebics:H005"><h:NumSegments>65</h:NumSegments></r>';
    rejects($post, 'Namespace prefix cannot bypass segment limit', 'segment count exceeds');
    $budget->end();
});

test('real SDK refuses excessive segment advertisement before another bank request', function (): void {
    [$path, $journal] = journal();
    $bank = new ScriptedBank(random_bytes(4096));
    $bank->segments = 1000;
    $receiver = new DownloadReceiver($journal);
    rejects(fn() => $receiver->receive($bank->client, request()), 'Segment admission', 'segment count exceeds');
    check(count($bank->phases) === 1 && $bank->receipts === 0, 'Initial response alone stops oversized segment set');
    check($journal->find(request()) === null, 'No original persisted from refused segment set');
    $bank->segments = 2;
    check($receiver->receive($bank->client, request())['receipt_state'] === 'confirmed', 'Transport budget resets after failed order');
});

test('expired receipt budget retains the committed original and prevents repeat transfer', function (): void {
    [$path, $journal] = journal();
    $bank = new ScriptedBank('committed before deadline');
    $now = 0.0;
    $budget = new DownloadBudget($bank, 'https://bank.invalid/ebics', static function () use (&$now): float { return $now; });
    $bank->onReceipt = static function () use (&$now): void { $now = DownloadBudget::MAX_SECONDS; };
    $client = $bank->clientWithTransport($budget);
    $receiver = new DownloadReceiver($journal);
    $budget->begin();
    try {
        rejects(fn() => $receiver->receive($client, request()), 'Receipt response exceeds deadline', 'response or time budget');
    } finally { $budget->end(); }
    check($bank->receipts === 1, 'Only durable original was acknowledged before late response');
    check($journal->payload(request()) === 'committed before deadline', 'Original survives late receipt response');
    check($journal->find(request())['receipt_state'] === 'unconfirmed', 'Late response does not invent a confirmed receipt');
    $before = count($bank->phases);
    check($receiver->receive($client, request())['replayed'], 'Stored request does not need active network budget');
    check(count($bank->phases) === $before, 'Uncertain receipt does not trigger repeat transfer');
});

test('real SDK rejects oversized or malformed zlib before original persistence and receipt', function (): void {
    foreach ([compressed_repeat(TransferJournal::MAX_BYTES + 1), 'malformed zlib'] as $compressed) {
        [$path, $journal] = journal();
        $bank = new ScriptedBank('valid recovery');
        $bank->compressedPayload = $compressed;
        $receiver = new DownloadReceiver($journal);
        rejects(fn() => $receiver->receive($bank->client, request()), 'Bounded pipe rejects before journal', 'Invalid or oversized zlib payload');
        check($bank->receipts === 0 && count($bank->phases) === 2, 'Signed segmented transfer stops before receipt');
        check($journal->find(request()) === null, 'No partial original recorded');
        $bank->compressedPayload = null;
        check($receiver->receive($bank->client, request())['receipt_state'] === 'confirmed', 'Valid transfer recovers after bounded rejection');
        check($journal->payload(request()) === 'valid recovery', 'Recovery bytes unchanged');
    }
});

test('read-only admission', function (): void {
    foreach (['pain.001.001.09', 'BTU', 'INI', 'https://bank.invalid', 'camt.053.001.04'] as $profile) {
        rejects(fn() => request(['profile' => $profile]), 'No non-read profile');
    }
    foreach (['../site', '', "site\n", str_repeat('x', 101)] as $site) rejects(fn() => request(['site' => $site]), 'Opaque ID');
    foreach (['2026-02-29', '2026-9-1', 'today', '2026-09-01T12:00:00Z'] as $from) rejects(fn() => request(['from' => $from]), 'Exact date');
    rejects(fn() => request(['until' => '2026-08-31']), 'No reversed interval');
    rejects(fn() => request(['until' => '2026-10-03']), 'Bounded interval');
    check(request(['until' => '2026-10-02'])->until === '2026-10-02', '32 inclusive days accepted');
    check(ReadRequest::date('2024-02-29')->getTimezone()->getName() === 'UTC', 'Leap date and UTC');
});

test('explicit private initialization and key binding', function (): void {
    global $root;
    rejects(fn() => new TransferJournal($root, 'key', random_bytes(32)), 'No automatic journal creation');
    check(!file_exists($root . '/transfers.sqlite'), 'Absent journal stays absent');
    [$path, $journal] = journal();
    $hash = hash_file('sha256', $path . '/transfers.sqlite');
    rejects(fn() => TransferJournal::initialize($path, 'test-key', str_repeat('K', 32)), 'No reinitialization');
    rejects(fn() => new TransferJournal($path, 'other-key', str_repeat('K', 32)), 'No different key ID');
    rejects(fn() => new TransferJournal($path, 'test-key', str_repeat('Z', 32)), 'No wrong key');
    check(hash_file('sha256', $path . '/transfers.sqlite') === $hash, 'Failed opens do not replace journal');
    chmod($path, 0755); clearstatcache();
    rejects(fn() => new TransferJournal($path, 'test-key', str_repeat('K', 32)), 'No shared directory');
    chmod($path, 0700); chmod($path . '/transfers.sqlite', 0644); clearstatcache();
    rejects(fn() => new TransferJournal($path, 'test-key', str_repeat('K', 32)), 'No shared database');
    chmod($path . '/transfers.sqlite', 0600); clearstatcache();
    symlink($path, $root . '/linked');
    rejects(fn() => new TransferJournal($root . '/linked', 'test-key', str_repeat('K', 32)), 'No symlink directory');
});

test('binary original, encryption, replay, scope and rollback', function (): void {
    [$path, $journal] = journal();
    $bytes = "PK\x03\x04\0\xff confidential-original-marker\0" . random_bytes(1000);
    $original = $journal->persist(request(), 'BANK01', 2, $bytes);
    check($original['receipt_state'] === 'unconfirmed', 'Receipt initially unknown');
    check($journal->payload(request()) === $bytes, 'Binary bytes preserved');
    check(!str_contains(file_get_contents($path . '/transfers.sqlite'), 'confidential-original-marker'), 'No plaintext original in database');
    $db = new PDO('sqlite:' . $path . '/transfers.sqlite');
    check($db->query('SELECT typeof(payload) FROM transfers')->fetchColumn() === 'blob', 'Ciphertext stored as BLOB');
    for ($i = 0; $i < 10; $i++) check($journal->persist(request(), 'BANK01', 2, $bytes) === $original, 'Identical replay');
    rejects(fn() => $journal->persist(request(), 'BANK02', 2, $bytes), 'Changed bank ID conflicts');
    rejects(fn() => $journal->persist(request(), 'BANK01', 1, $bytes), 'Changed segment count conflicts');
    rejects(fn() => $journal->persist(request(), 'BANK01', 2, 'changed'), 'Changed original conflicts');
    foreach (['participant', 'profile', 'until'] as $key) {
        $value = ['participant' => 'other', 'profile' => 'camt.054.001.08', 'until' => '2026-09-03'][$key];
        rejects(fn() => $journal->find(request([$key => $value])), 'Reused request ID cannot change binding');
    }
    check($journal->find(request(['site' => 'other'])) === null, 'Other site has no access through same request ID');
    check($journal->find(request(['connection' => 'other'])) === null, 'Other connection isolated');
    $journal->persist(request(['request' => 'after-conflict']), 'BANK02', 1, 'after rollback');
    check($journal->payload(request(['request' => 'after-conflict'])) === 'after rollback', 'Connection usable after rollback');
    check((int)$db->query('SELECT count(*) FROM transfers')->fetchColumn() === 2, 'No duplicate records');
    rejects(fn() => $journal->confirm(request(), 'WRONG', '<receipt/>'), 'Cannot confirm another bank transaction');
    check($journal->confirm(request(), 'BANK01', '<receipt>secret-receipt-marker</receipt>')['receipt_state'] === 'confirmed', 'Receipt recorded');
    check(!str_contains(file_get_contents($path . '/transfers.sqlite'), 'secret-receipt-marker'), 'Receipt encrypted');
});

test('tamper detection for original metadata and receipt', function (): void {
    foreach (['payload', 'payload_hash', 'payload_bytes', 'segments', 'bank_id', 'received_at', 'receipt'] as $column) {
        [$path, $journal] = journal();
        $journal->persist(request(), 'BANK01', 1, 'original');
        $journal->confirm(request(), 'BANK01', '<receipt/>');
        $db = new PDO('sqlite:' . $path . '/transfers.sqlite');
        $db->exec('UPDATE transfers SET ' . $column . "='tampered'");
        rejects(fn() => $journal->find(request()), 'Tampering rejected for ' . $column);
    }
});

test('native SQLite restart and cross-process participant exclusion', function (): void {
    [$path, $journal] = journal();
    check(worker('persist', $path) === [0, ''], 'Independent writer commits');
    check(worker('read', $path) === [0, 'restart original'], 'New process recovers exact original');
    $journal->exclusive(request(), function () use ($path): void {
        check(worker('lock', $path) === [23, 'blocked'], 'Second process is excluded');
    });
    check(worker('lock', $path) === [0, 'acquired'], 'Lock released after successful operation');
    rejects(fn() => $journal->exclusive(request(), fn() => throw new RuntimeException('test interruption')), 'Interrupted owner');
    check(worker('lock', $path) === [0, 'acquired'], 'Lock released after interrupted operation');
});

test('handover envelope exports authenticated original without changing receipt state', function (): void {
    [$path, $journal] = journal();
    rejects(fn() => $journal->handover(request()), 'Cannot export missing original');
    $bytes = "PK\x03\x04\x00\xff" . random_bytes(256);
    $before = $journal->persist(request(), 'BANK01', 2, $bytes);
    $export = $journal->handover(request());
    check($export['payload'] === $bytes, 'Export retains binary bytes');
    check($export['metadata']['request'] === get_object_vars(request()), 'Complete immutable request scope');
    check($export['metadata']['request_key'] === request()->key(), 'Same cross-language request identity');
    check($export['metadata']['archive_sha256'] === hash('sha256', $bytes), 'Original hash bound');
    check($journal->find(request()) === $before, 'No invented ERP or bank acknowledgement');
    rejects(fn() => $journal->handover(request(['participant' => 'other'])), 'Cannot export another participant');
    $db = new PDO('sqlite:' . $path . '/transfers.sqlite');
    $db->exec("UPDATE transfers SET payload_hash='tampered'");
    rejects(fn() => $journal->handover(request()), 'Cannot export altered authenticated metadata');
});

test('real EBICS SDK persists before signed positive receipt and does not resend', function (): void {
    foreach (['camt.053.001.08' => 'EOP', 'camt.054.001.08' => 'REP'] as $profile => $service) {
        [$path, $journal] = journal();
        $req = request(['profile' => $profile]);
        $bank = new ScriptedBank("PK\x03\x04 test zip original " . random_bytes(64));
        $bank->onReceipt = function () use ($path, $req): void {
            $reopened = new TransferJournal($path, 'test-key', str_repeat('K', 32));
            check($reopened->find($req)['receipt_state'] === 'unconfirmed', 'Independent connection sees original before acknowledgement');
            check(strlen($reopened->payload($req)) > 0, 'Original can be decrypted before acknowledgement');
        };
        $receiver = new DownloadReceiver($journal);
        $result = $receiver->receive($bank->client, $req);
        check($result['receipt_state'] === 'confirmed' && $result['replayed'] === false, 'Signed receipt completes transfer');
        check($bank->receipts === 1 && count($bank->phases) === 3, 'Two segments and one receipt');
        check(str_contains($bank->requests[0], '<ServiceName>' . $service . '</ServiceName>'), 'Correct BTF service');
        check(str_contains($bank->requests[0], '<Scope>CH</Scope>'), 'Swiss BTF scope');
        check(str_contains($bank->requests[0], 'containerType="ZIP"'), 'ZIP container requested');
        check(str_contains($bank->requests[0], 'version="08">' . substr($profile, 0, 8)), 'Exact camt version');
        for ($i = 0; $i < 10; $i++) check($receiver->receive($bank->client, $req)['replayed'], 'Stored retry is local');
        check(count($bank->phases) === 3, 'Retries do not contact simulated bank');
    }
});

test('SIGKILL during receipt retains committed original across processes', function (): void {
    [$path, $journal] = journal();
    [$code, $output] = worker('receipt-crash', $path);
    check($code !== 0 && $output === 'committed-before-kill', 'Child was killed at receipt, not a setup failure');
    $req = request(['request' => 'restart']);
    $reopened = new TransferJournal($path, 'test-key', str_repeat('K', 32));
    check($reopened->payload($req) === 'original before hard process termination', 'Original survives abrupt process death');
    check($reopened->find($req)['receipt_state'] === 'unconfirmed', 'No invented confirmation after process death');
    $bank = new ScriptedBank('must never be requested');
    $replay = (new DownloadReceiver($reopened))->receive($bank->client, $req);
    check($replay['replayed'] && $replay['receipt_state'] === 'unconfirmed', 'Recovery reports uncertainty and releases process lock');
    check($bank->phases === [], 'Restart does not repeat request');
});

test('real SDK receipt timeout or error retains original without positive local state', function (): void {
    foreach (['receipt_timeout', 'receipt_error'] as $mode) {
        [$path, $journal] = journal();
        $bank = new ScriptedBank('durable before uncertain receipt');
        $bank->mode = $mode;
        $receiver = new DownloadReceiver($journal);
        rejects(fn() => $receiver->receive($bank->client, request()), 'Receipt fails');
        check($journal->payload(request()) === 'durable before uncertain receipt', 'Original survives receipt failure');
        check($journal->find(request())['receipt_state'] === 'unconfirmed', 'Uncertain receipt not marked confirmed');
        $before = count($bank->phases);
        check($receiver->receive($bank->client, request())['replayed'], 'Uncertain request uses original');
        check(count($bank->phases) === $before, 'No automatic repeat transfer');
    }
});

test('real SDK storage failure prevents positive receipt', function (): void {
    [$path, $journal] = journal();
    $db = new PDO('sqlite:' . $path . '/transfers.sqlite');
    $db->exec("CREATE TRIGGER fail_store BEFORE INSERT ON transfers BEGIN SELECT RAISE(ABORT, 'test storage failure'); END");
    $bank = new ScriptedBank('must not acknowledge');
    $receiver = new DownloadReceiver($journal);
    rejects(fn() => $receiver->receive($bank->client, request()), 'Write failure propagates', 'test storage failure');
    check($bank->receipts === 0, 'Bank receives no acknowledgement on storage failure');
    check($journal->find(request()) === null, 'No partial row');
    $db->exec('DROP TRIGGER fail_store');
    check($receiver->receive($bank->client, request())['receipt_state'] === 'confirmed', 'Recovery after write failure');
});

test('real SDK rejects invalid bank response signature before persistence', function (): void {
    [$path, $journal] = journal();
    $bank = new ScriptedBank('unauthenticated');
    $bank->mode = 'invalid_signature';
    try {
        (new DownloadReceiver($journal))->receive($bank->client, request());
        check(false, 'Invalid bank signature accepted');
    } catch (EbicsApi\Ebics\Exceptions\SignatureEbicsException) {
        check(count($bank->phases) === 1, 'Response signature fails after first actual request, not during setup');
    }
    check($bank->receipts === 0, 'No acknowledgement for invalid signature');
    check($journal->find(request()) === null, 'No accepted original for invalid signature');
});

echo json_encode(['assertions' => $assertions, 'failed_groups' => $failures, 'network' => 'scripted-http-only'], JSON_THROW_ON_ERROR) . "\n";
exit($failures === 0 ? 0 : 1);
