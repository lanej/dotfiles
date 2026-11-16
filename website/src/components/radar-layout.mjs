/** @typedef {{ id: string, name: string, anchor: string, icon: string }} RadarEntry */
/** @typedef {{ name: string, entries: RadarEntry[] }} RadarRing */

/** @param {RadarRing[]} rings */
export function layoutRadar(rings) {
  let outerRadius = 0;
  const bands = rings.map((ring, index) => {
    const count = ring.entries.length;
    const step = count > 1 ? (230 / (count - 1)) * Math.PI / 180 : 0;
    // rationale(spacing): Keep the 58-unit hit targets apart as registry rings grow.
    const minimumRadius = count > 1 ? 62 / (2 * Math.sin(step / 2)) : 0;
    const pointRadius = Math.max(index === 0 ? 36 : outerRadius + 39, minimumRadius);
    outerRadius = pointRadius + 26;
    return { ...ring, key: ring.name.toLowerCase(), radius: outerRadius, pointRadius };
  });
  const center = outerRadius + 43;
  return {
    center,
    size: center * 2,
    rings: bands.map((ring) => ({
      ...ring,
      entries: ring.entries.map((entry, index) => {
        const angle = (ring.entries.length === 1 ? 90 : -25 + (index * 230) / (ring.entries.length - 1)) * Math.PI / 180;
        return { ...entry, x: center + Math.cos(angle) * ring.pointRadius, y: center + Math.sin(angle) * ring.pointRadius };
      }),
    })),
  };
}
