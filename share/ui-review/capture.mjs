export const detailDefaults = {
  width: 1024,
  height: 800,
  overlap: 64,
  maxTiles: 64,
};

export function tilePlan(width, height, options = detailDefaults) {
  const starts = (length, size) => {
    if (length <= size) return [0];
    const steps = Math.ceil((length - size) / (size - options.overlap));
    return Array.from({ length: steps + 1 }, (_, i) =>
      Math.round((i * (length - size)) / steps),
    );
  };
  const tiles = [];
  for (const y of starts(height, options.height)) {
    for (const x of starts(width, options.width)) {
      tiles.push({
        x,
        y,
        width: Math.min(width, options.width),
        height: Math.min(height, options.height),
      });
    }
  }
  return tiles;
}

export async function captureDetails(
  page,
  directory,
  prefix,
  options = detailDefaults,
) {
  const { default: path } = await import("node:path");
  const dimensions = await page.evaluate(() => ({
    width: Math.max(
      document.documentElement.clientWidth,
      document.documentElement.scrollWidth,
    ),
    height: Math.max(innerHeight, document.documentElement.scrollHeight),
  }));
  const planned = tilePlan(dimensions.width, dimensions.height, options);
  const tiles = [];
  for (const clip of planned.slice(0, options.maxTiles)) {
    const file = `${prefix}-detail-${tiles.length + 1}.png`;
    const png = await page.screenshot({
      path: path.join(directory, file),
      fullPage: true,
      clip,
      animations: "disabled",
    });
    // Device scale is one: CSS-pixel tiles must retain their exact pixel dimensions.
    if (
      png.readUInt32BE(16) !== clip.width ||
      png.readUInt32BE(20) !== clip.height
    ) {
      throw new Error(
        "Detail capture dimensions changed; cannot assert full-resolution coverage.",
      );
    }
    tiles.push({ file, ...clip });
  }
  return {
    ...dimensions,
    scale: 1,
    expectedTiles: planned.length,
    capturedTiles: tiles.length,
    complete: tiles.length === planned.length,
    tiles,
  };
}
