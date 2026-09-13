const assert = require("node:assert/strict");
const { test } = require("node:test");
const { PNG } = require("pngjs");
const { compareScreenshots } = require("./compare-screenshots.cjs");

function sample(pixels = 0, delta = 1, width = 16) {
    const png = new PNG({ width, height: 16 });
    png.data.fill(255);
    for (let index = 0; index < pixels; index++) png.data[index * 4] -= delta;
    return PNG.sync.write(png);
}

test("identical screenshots need no tolerance", () => {
    assert.deepEqual(compareScreenshots(sample(), sample(), "same"),
        { changedPixels: 0, maxChannelDifference: 0 });
});

test("only bounded one-level rasterization differences are accepted", () => {
    assert.deepEqual(compareScreenshots(sample(128), sample(), "rounding"),
        { changedPixels: 128, maxChannelDifference: 1 });
    assert.throws(() => compareScreenshots(sample(129), sample(), "too many"), /128 pixels/);
    assert.throws(() => compareScreenshots(sample(1, 2), sample(), "too dark"), /1\/255/);
});

test("dimension changes are rejected", () => {
    assert.throws(() => compareScreenshots(sample(0, 1, 17), sample(), "resized"), /width/);
});
