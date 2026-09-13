<?php
declare(strict_types=1);
// Only a loopback fixture server in the isolated test container; no proxy or bank.
if (getenv('KT_GATEWAY_HTTPS_TEST') !== '1' || posix_geteuid() !== 10001) exit(2);
$directory = realpath($argv[1]);
if ($directory === false || !str_starts_with($directory, '/tmp/kt-https-')) exit(2);
$context = stream_context_create(['ssl' => ['local_cert' => $directory . '/cert.pem',
    'local_pk' => $directory . '/key.pem', 'verify_peer' => false]]);
$server = stream_socket_server('tls://127.0.0.1:0', $errno, $error,
    STREAM_SERVER_BIND | STREAM_SERVER_LISTEN, $context);
if (!$server) throw new RuntimeException('Cannot start isolated TLS fixture');
echo stream_socket_get_name($server, false) . "\n";
flush();
$bankIndex = 0;
function send_all($client, string $bytes): bool {
    $sent = 0;
    while ($sent < strlen($bytes)) {
        $count = @fwrite($client, substr($bytes, $sent));
        if (!$count) return false;
        $sent += $count;
    }
    return true;
}
for ($attempt = 0; $attempt < 100; $attempt++) {
    $client = @stream_socket_accept($server, 10);
    if (!$client) continue;
    stream_set_timeout($client, 2);
    $first = fgets($client);
    if ($first === false) { fclose($client); continue; }
    $path = explode(' ', trim($first))[1] ?? '';
    file_put_contents($directory . '/requests.log', $path . "\n", FILE_APPEND);
    $length = 0;
    while (($line = fgets($client)) !== false && trim($line) !== '') {
        if (stripos($line, 'Content-Length:') === 0) $length = (int)trim(substr($line, 15));
    }
    if ($length < 0 || $length > 1048576) { fclose($client); continue; }
    $content = '';
    while (strlen($content) < $length && !feof($client)) {
        $chunk = fread($client, min(8192, $length - strlen($content)));
        if ($chunk === false || $chunk === '') break;
        $content .= $chunk;
    }
    if ($path === '/slow') usleep(600000);
    $body = '<response>safe &amp; exact</response>';
    $headers = 'HTTP/1.1 200 OK' . "\r\nConnection: close\r\n";
    if ($path === '/exact') $body = '<r>' . str_repeat('X', 8388608 - 7) . '</r>';
    if (in_array($path, ['/oversized', '/chunked'], true)) $body = str_repeat('X', 8388609);
    if ($path === '/headers') $headers .= str_repeat('X-Test: ' . str_repeat('x', 900) . "\r\n", 75);
    if ($path === '/redirect') $headers = "HTTP/1.1 302 Found\r\nLocation: /target\r\nConnection: close\r\n";
    if ($path === '/encoded') $headers .= "Content-Encoding: gzip\r\n";
    if ($path === '/empty') $body = '';
    if ($path === '/malformed') $body = '<private-server-body';
    if ($path === '/error') { $headers = "HTTP/1.1 500 Error\r\nConnection: close\r\n"; $body = 'private-server-body'; }
    if ($path === '/bank') $body = file_get_contents($directory . '/bank-' . ++$bankIndex . '.xml');
    $headers .= $path === '/chunked' ? "Transfer-Encoding: chunked\r\n\r\n" : 'Content-Length: ' . strlen($body) . "\r\n\r\n";
    send_all($client, $headers);
    foreach (str_split($body, 8192) as $chunk) {
        $chunk = $path === '/chunked' ? dechex(strlen($chunk)) . "\r\n" . $chunk . "\r\n" : $chunk;
        if (!send_all($client, $chunk)) break;
    }
    if ($path === '/chunked') send_all($client, "0\r\n\r\n");
    fclose($client);
}
