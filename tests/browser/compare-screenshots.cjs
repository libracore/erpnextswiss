const assert = require("node:assert/strict");
const { PNG } = require("pngjs");

function compareScreenshots(actual, reference, label) {
    if (actual.equals(reference)) return { changedPixels: 0, maxChannelDifference: 0 };
    const a = PNG.sync.read(actual);
    const b = PNG.sync.read(reference);
    assert.equal(a.width, b.width, "Screenshot width: " + label);
    assert.equal(a.height, b.height, "Screenshot height: " + label);
    let changedPixels = 0;
    let maxChannelDifference = 0;
    for (let offset = 0; offset < a.data.length; offset += 4) {
        let delta = 0;
        for (let channel = 0; channel < 4; channel++) {
            delta = Math.max(delta, Math.abs(a.data[offset + channel] - b.data[offset + channel]));
        }
        maxChannelDifference = Math.max(maxChannelDifference, delta);
        if (delta) changedPixels++;
        // Cold/warm Chromium rasterization differed by one grayscale level at
        // 36 rounded-edge pixels. Do not mask regions or tolerate real shifts.
        assert.ok(delta <= 1, "Screenshot channel difference exceeds 1/255: " + label);
        assert.ok(changedPixels <= 128, "Screenshot differs at more than 128 pixels: " + label);
    }
    return { changedPixels, maxChannelDifference };
}

module.exports = { compareScreenshots };
