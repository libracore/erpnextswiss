<?php
declare(strict_types=1);

namespace KT\Banking;

use PDO;
use RuntimeException;
use Throwable;

final class TransferJournal
{
    private PDO $db;
    private string $directory;
    public const MAX_BYTES = 33554432;

    public function __construct(string $directory, private readonly string $keyId, private readonly string $key)
    {
        $this->directory = self::directory($directory);
        self::key($keyId, $key);
        $this->db = self::connect($this->directory);
        $header = $this->db->query('SELECT key_id, verifier FROM journal_info WHERE version=1')->fetch(PDO::FETCH_ASSOC);
        if (!$header || $header['key_id'] !== $keyId || $this->decrypt($header['verifier'], 'journal-key:' . $keyId) !== 'KT bank journal v1') {
            throw new RuntimeException('Journal key does not match; no automatic initialization or rotation');
        }
    }

    public static function initialize(string $directory, string $keyId, string $key): void
    {
        $directory = self::directory($directory);
        self::key($keyId, $key);
        if (file_exists($directory . '/transfers.sqlite') || is_link($directory . '/transfers.sqlite')) {
            throw new RuntimeException('Existing journal must never be reinitialized');
        }
        $mask = umask(0077);
        try {
            $handle = fopen($directory . '/transfers.sqlite', 'x');
        } finally {
            umask($mask);
        }
        if (!$handle) {
            throw new RuntimeException('Cannot create private journal');
        }
        chmod($directory . '/transfers.sqlite', 0600);
        fclose($handle);
        $db = self::connect($directory);
        $db->beginTransaction();
        try {
            $db->exec('CREATE TABLE journal_info(version INTEGER PRIMARY KEY CHECK(version=1), key_id TEXT NOT NULL, verifier BLOB NOT NULL)');
            $db->exec('CREATE TABLE transfers(request_key TEXT PRIMARY KEY, binding TEXT NOT NULL, bank_id TEXT NOT NULL, segments INTEGER NOT NULL,
                payload_hash TEXT NOT NULL, payload_bytes INTEGER NOT NULL, received_at TEXT NOT NULL, payload BLOB NOT NULL, receipt BLOB)');
            $statement = $db->prepare('INSERT INTO journal_info VALUES(1, ?, ?)');
            $statement->bindValue(1, $keyId);
            $statement->bindValue(2, self::encryptWith($key, 'KT bank journal v1', 'journal-key:' . $keyId), PDO::PARAM_LOB);
            $statement->execute();
            $db->commit();
        } catch (Throwable $error) {
            if ($db->inTransaction()) $db->rollBack();
            throw $error;
        }
    }

    private static function directory(string $directory): string
    {
        $path = realpath($directory);
        if (!$path || is_link($directory) || !is_dir($path) || (fileperms($path) & 0077) !== 0 || fileowner($path) !== posix_geteuid()) {
            throw new RuntimeException('Existing owner-only journal directory required');
        }
        return $path;
    }

    private static function key(string $id, string $key): void
    {
        if (!preg_match('/\A[a-zA-Z0-9_-]{1,100}\z/', $id) || strlen($key) !== SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_KEYBYTES) {
            throw new RuntimeException('Explicit secret key and opaque key ID required');
        }
    }

    private static function connect(string $directory): PDO
    {
        $file = $directory . '/transfers.sqlite';
        if (!is_file($file) || is_link($file) || (fileperms($file) & 0077) !== 0 || fileowner($file) !== posix_geteuid()) {
            throw new RuntimeException('Existing private regular journal required');
        }
        $db = new PDO('sqlite:' . $file, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
        $db->exec('PRAGMA busy_timeout=5000');
        $mode = $db->query('PRAGMA journal_mode=DELETE')->fetchColumn();
        $db->exec('PRAGMA synchronous=EXTRA');
        if (strtolower($mode) !== 'delete' || (int)$db->query('PRAGMA synchronous')->fetchColumn() !== 3) {
            throw new RuntimeException('Durable SQLite rollback-journal settings unavailable');
        }
        return $db;
    }

    public function exclusive(ReadRequest $request, callable $work): mixed
    {
        // A participant lock is never deleted: replacing its inode would split ownership.
        $path = $this->directory . '/participant-' . hash('sha256', $request->participant) . '.lock';
        if (is_link($path) || (file_exists($path) && (!is_file($path) || fileowner($path) !== posix_geteuid()))) {
            throw new RuntimeException('Invalid participant lock');
        }
        $mask = umask(0077);
        try {
            $lock = fopen($path, 'c');
        } finally {
            umask($mask);
        }
        if (!$lock) throw new RuntimeException('Cannot open participant lock');
        chmod($path, 0600);
        try {
            if (!flock($lock, LOCK_EX | LOCK_NB)) throw new RuntimeException('Participant transport is already running');
            return $work();
        } finally {
            flock($lock, LOCK_UN);
            fclose($lock);
        }
    }

    public function persist(ReadRequest $request, string $bankId, int $segments, string $payload): array
    {
        if (!preg_match('/\A[a-zA-Z0-9_-]{1,100}\z/', $bankId) || $segments < 1 || $segments > 10000
            || strlen($payload) < 1 || strlen($payload) > self::MAX_BYTES) {
            throw new RuntimeException('Transfer identity, segment count or size outside limits');
        }
        $this->db->exec('BEGIN IMMEDIATE');
        try {
            $existing = $this->find($request);
            if ($existing) {
                if ($existing['bank_id'] !== $bankId || $existing['segments'] !== $segments
                    || !hash_equals($existing['payload_hash'], hash('sha256', $payload))) {
                    throw new RuntimeException('Conflicting transfer for an existing request');
                }
                $this->db->exec('COMMIT');
                return $existing;
            }
            $row = ['request_key' => $request->key(), 'binding' => $request->binding(), 'bank_id' => $bankId, 'segments' => $segments,
                'payload_hash' => hash('sha256', $payload), 'payload_bytes' => strlen($payload), 'received_at' => gmdate('Y-m-d\TH:i:s\Z')];
            $encrypted = self::encryptWith($this->key, $payload, $this->aad($row, 'payload'));
            $statement = $this->db->prepare('INSERT INTO transfers(request_key,binding,bank_id,segments,payload_hash,payload_bytes,received_at,payload)
                VALUES(:request_key,:binding,:bank_id,:segments,:payload_hash,:payload_bytes,:received_at,:payload)');
            foreach ($row as $name => $value) {
                $statement->bindValue(':' . $name, $value, is_int($value) ? PDO::PARAM_INT : PDO::PARAM_STR);
            }
            $statement->bindValue(':payload', $encrypted, PDO::PARAM_LOB);
            $statement->execute();
            $this->db->exec('COMMIT');
        } catch (Throwable $error) {
            // PDO does not track transactions opened using SQLite BEGIN IMMEDIATE.
            try {
                $this->db->exec('ROLLBACK');
            } catch (Throwable) {
                // Preserve the original storage failure (SQLite can auto-rollback on full disk).
            }
            throw $error;
        }
        // Read back through an independent connection before allowing positive EBICS receipt.
        return (new self($this->directory, $this->keyId, $this->key))->find($request)
            ?? throw new RuntimeException('Committed transfer cannot be read back');
    }

    public function find(ReadRequest $request): ?array
    {
        $statement = $this->db->prepare('SELECT * FROM transfers WHERE request_key=?');
        $statement->execute([$request->key()]);
        $row = $statement->fetch(PDO::FETCH_ASSOC);
        if (!$row) return null;
        if ($row['binding'] !== $request->binding()) throw new RuntimeException('Request identity reused for a different scope');
        $payload = $this->decrypt($row['payload'], $this->aad($row, 'payload'));
        if (strlen($payload) !== $row['payload_bytes'] || !hash_equals($row['payload_hash'], hash('sha256', $payload))) {
            throw new RuntimeException('Stored transfer integrity failed');
        }
        $receipt = $row['receipt'] === null ? null : $this->decrypt($row['receipt'], $this->aad($row, 'receipt'));
        unset($row['payload'], $row['receipt']);
        return [...$row, 'receipt_state' => $receipt === null ? 'unconfirmed' : 'confirmed'];
    }

    public function payload(ReadRequest $request): string
    {
        $row = $this->find($request) ?? throw new RuntimeException('Transfer not found');
        $statement = $this->db->prepare('SELECT payload FROM transfers WHERE request_key=?');
        $statement->execute([$request->key()]);
        return $this->decrypt($statement->fetchColumn(), $this->aad($row, 'payload'));
    }

    public function handover(ReadRequest $request): array
    {
        // Export only an authenticated local original. No bank request, receipt
        // change or ERP success state is implied by preparing this envelope.
        $row = $this->find($request) ?? throw new RuntimeException('Transfer not found');
        $payload = $this->payload($request);
        if (strlen($payload) !== $row['payload_bytes'] || !hash_equals($row['payload_hash'], hash('sha256', $payload))) {
            throw new RuntimeException('Exported original integrity failed');
        }
        return ['metadata' => ['version' => 1, 'request' => get_object_vars($request), 'request_key' => $request->key(),
            'bank_id' => $row['bank_id'], 'segments' => $row['segments'], 'archive_sha256' => $row['payload_hash'],
            'archive_bytes' => $row['payload_bytes'], 'received_at' => $row['received_at'], 'receipt_state' => $row['receipt_state']],
            'payload' => $payload];
    }

    public function confirm(ReadRequest $request, string $bankId, string $verifiedReceipt): array
    {
        if ($verifiedReceipt === '' || strlen($verifiedReceipt) > 2097152) throw new RuntimeException('Verified receipt required');
        $row = $this->find($request) ?? throw new RuntimeException('Cannot acknowledge absent original');
        if ($row['bank_id'] !== $bankId) throw new RuntimeException('Receipt transaction differs from persisted original');
        $receipt = self::encryptWith($this->key, $verifiedReceipt, $this->aad($row, 'receipt'));
        $statement = $this->db->prepare('UPDATE transfers SET receipt=? WHERE request_key=? AND receipt IS NULL');
        $statement->bindValue(1, $receipt, PDO::PARAM_LOB);
        $statement->bindValue(2, $request->key());
        $statement->execute();
        return $this->find($request);
    }

    private function aad(array $row, string $purpose): string
    {
        return json_encode(['kt-bank-journal-v1', $this->keyId, $purpose, $row['request_key'], $row['binding'], $row['bank_id'],
            (int)$row['segments'], $row['payload_hash'], (int)$row['payload_bytes'], $row['received_at']], JSON_THROW_ON_ERROR);
    }

    private static function encryptWith(string $key, string $bytes, string $aad): string
    {
        $nonce = random_bytes(SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES);
        return $nonce . sodium_crypto_aead_xchacha20poly1305_ietf_encrypt($bytes, $aad, $nonce, $key);
    }

    private function decrypt(string $ciphertext, string $aad): string
    {
        $length = SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES;
        if (strlen($ciphertext) < $length + SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_ABYTES) throw new RuntimeException('Invalid journal ciphertext');
        $bytes = sodium_crypto_aead_xchacha20poly1305_ietf_decrypt(substr($ciphertext, $length), $aad, substr($ciphertext, 0, $length), $this->key);
        if ($bytes === false) throw new RuntimeException('Journal authentication failed');
        return $bytes;
    }
}
