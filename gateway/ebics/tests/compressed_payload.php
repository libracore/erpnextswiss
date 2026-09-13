<?php
declare(strict_types=1);

// Generate synthetic high-expansion data without ever allocating the expanded size.
function compressed_repeat(int $bytes): string
{
    $context = deflate_init(ZLIB_ENCODING_DEFLATE);
    if ($context === false || $bytes < 0) throw new RuntimeException('Invalid synthetic deflate setup');
    $result = '';
    while ($bytes > 0) {
        $size = min($bytes, 1048576);
        $part = deflate_add($context, str_repeat('X', $size), ZLIB_NO_FLUSH);
        if ($part === false) throw new RuntimeException('Synthetic deflate failed');
        $result .= $part;
        $bytes -= $size;
    }
    $end = deflate_add($context, '', ZLIB_FINISH);
    if ($end === false) throw new RuntimeException('Synthetic deflate finalization failed');
    return $result . $end;
}
