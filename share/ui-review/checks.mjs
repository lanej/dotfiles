// Runs inside the page. Selectors and thresholds come from validated configuration.
// Hidden responsive variants don't count. Group checks apply only to declared peers.
export function inspectPage(rules) {
  const findings = [];
  const density = [];
  const rect = (el) => el.getBoundingClientRect();
  const visible = (el) => {
    const r = rect(el);
    return (
      r.width > 0 &&
      r.height > 0 &&
      el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })
    );
  };
  const describe = (el) =>
    el.id
      ? `#${el.id}`
      : el.tagName.toLowerCase() +
        (el.classList.length ? "." + [...el.classList].join(".") : "");
  const add = (rule, message, el, actual, expected) =>
    findings.push({
      rule: rule.id,
      severity: rule.severity,
      selector: rule.selector,
      element: el ? describe(el) : null,
      message,
      reason: rule.reason,
      actual,
      expected,
      box: el
        ? (() => {
            const r = rect(el);
            return {
              x: r.x + scrollX,
              y: r.y + scrollY,
              width: r.width,
              height: r.height,
            };
          })()
        : null,
    });
  const width = document.documentElement.clientWidth;
  const overflow =
    Math.max(
      document.documentElement.scrollWidth,
      document.body?.scrollWidth ?? 0,
    ) - width;
  if (overflow > 1)
    add(
      {
        id: "page-overflow",
        severity: "error",
        selector: "html",
        reason:
          "Keep page content within the viewport; use intentional local scroll regions.",
      },
      `Page overflows horizontally by ${overflow}px.`,
      null,
      overflow,
      0,
    );
  let evaluated = 0;
  for (const rule of rules) {
    const els = [...document.querySelectorAll(rule.selector)].filter(visible);
    evaluated++;
    if (!els.length) {
      if (!rule.optional)
        add(
          rule,
          "Required selector has no visible matches.",
          null,
          0,
          "at least one visible match",
        );
      continue;
    }
    if (rule.type === "region-density") {
      const regions =
        rule.region === "viewport"
          ? [document.documentElement]
          : [...document.querySelectorAll(rule.region)].filter(visible);
      if (regions.length !== 1) {
        add(
          rule,
          "Density region must match exactly one visible element.",
          null,
          regions.length,
          1,
        );
        continue;
      }
      const region = regions[0],
        r =
          rule.region === "viewport"
            ? { left: 0, right: width, top: 0, bottom: innerHeight }
            : rect(region);
      const bounds = {
        left: Math.max(0, r.left),
        right: Math.min(width, r.right),
        top: Math.max(0, r.top),
        bottom: Math.min(innerHeight, r.bottom),
      };
      if (bounds.right <= bounds.left || bounds.bottom <= bounds.top) {
        add(
          rule,
          "Density region is outside the initial viewport.",
          region,
          "offscreen",
          "visible region",
        );
        continue;
      }
      const selected = els.filter((el) => region.contains(el));
      const rectangles = [];
      for (const el of selected) {
        let boxes;
        if (rule.measure === "text") {
          boxes = [];
          const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            if (!node.textContent.trim() || !visible(node.parentElement))
              continue;
            const range = document.createRange();
            range.selectNodeContents(node);
            boxes.push(...range.getClientRects());
          }
        } else boxes = [rect(el)];
        for (const b of boxes) {
          const clipped = {
            left: Math.max(bounds.left, b.left),
            right: Math.min(bounds.right, b.right),
            top: Math.max(bounds.top, b.top),
            bottom: Math.min(bounds.bottom, b.bottom),
          };
          if (clipped.right > clipped.left && clipped.bottom > clipped.top)
            rectangles.push(clipped);
        }
      }
      const unionLength = (intervals) => {
        let total = 0,
          end = -Infinity;
        for (const [a, b] of intervals.sort((a, b) => a[0] - b[0])) {
          total += Math.max(0, b - Math.max(a, end));
          end = Math.max(end, b);
        }
        return total;
      };
      const xs = [
        ...new Set(rectangles.flatMap((b) => [b.left, b.right])),
      ].sort((a, b) => a - b);
      let area = 0;
      for (let i = 1; i < xs.length; i++)
        area +=
          (xs[i] - xs[i - 1]) *
          unionLength(
            rectangles
              .filter((b) => b.left < xs[i] && b.right > xs[i - 1])
              .map((b) => [b.top, b.bottom]),
          );
      let edge = bounds.top,
        gap = 0;
      for (const b of [...rectangles].sort((a, b) => a.top - b.top)) {
        gap = Math.max(gap, b.top - edge);
        edge = Math.max(edge, b.bottom);
      }
      gap = Math.max(gap, bounds.bottom - edge);
      const regionArea =
        (bounds.right - bounds.left) * (bounds.bottom - bounds.top);
      const coverage = area / regionArea;
      const count = selected.filter((el) => {
        const b = rect(el);
        return (
          b.right > bounds.left &&
          b.left < bounds.right &&
          b.bottom > bounds.top &&
          b.top < bounds.bottom
        );
      }).length;
      density.push({
        rule: rule.id,
        region: rule.region,
        measure: rule.measure,
        coverage,
        selectedElements: count,
        elementsPer100kPixels: (count / regionArea) * 100000,
        largestVerticalGap: gap,
        regionArea,
        coveredArea: area,
      });
      if (coverage < rule.minCoverage)
        add(
          rule,
          `Selected content covers ${(coverage * 100).toFixed(1)}% of the visible region.`,
          region,
          coverage,
          rule.minCoverage,
        );
      if (gap > rule.maxVerticalGap)
        add(
          rule,
          `Largest empty vertical band is ${gap.toFixed(1)}px.`,
          region,
          gap,
          rule.maxVerticalGap,
        );
    } else if (rule.type === "align") {
      if (els.length < 2) {
        add(
          rule,
          "Alignment needs at least two visible peers.",
          els[0],
          els.length,
          2,
        );
        continue;
      }
      const values = els.map((el) => rect(el)[rule.edge]);
      const spread = Math.max(...values) - Math.min(...values);
      if (spread > rule.tolerance)
        add(
          rule,
          `${rule.edge} edges differ by ${spread.toFixed(1)}px.`,
          els[values.indexOf(Math.max(...values))],
          spread,
          rule.tolerance,
        );
    } else if (rule.type === "visible-count") {
      const n = els.filter((el) => {
        const r = rect(el);
        return (
          r.top >= 0 &&
          r.bottom <= innerHeight &&
          r.left >= 0 &&
          r.right <= width
        );
      }).length;
      if (n < rule.min)
        add(
          rule,
          `Only ${n} complete items fit in the initial viewport.`,
          els[0],
          n,
          rule.min,
        );
    } else if (rule.type === "no-overlap") {
      for (let i = 0; i < els.length; i++)
        for (let j = i + 1; j < els.length; j++) {
          if (els[i].contains(els[j]) || els[j].contains(els[i])) continue;
          const a = rect(els[i]),
            b = rect(els[j]);
          if (
            Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
            Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1
          )
            add(
              rule,
              `Overlaps peer ${describe(els[j])}.`,
              els[i],
              "overlap",
              "no overlap",
            );
        }
    } else
      for (const el of els) {
        if (rule.type === "max-height" && rect(el).height > rule.max)
          add(
            rule,
            `Height is ${rect(el).height}px.`,
            el,
            rect(el).height,
            rule.max,
          );
        if (rule.type === "style") {
          const value = getComputedStyle(el)
            .getPropertyValue(rule.property)
            .trim();
          if (!rule.allowed.includes(value))
            add(
              rule,
              `Unapproved ${rule.property}: ${value}.`,
              el,
              value,
              rule.allowed,
            );
        }
        if (rule.type === "context")
          for (const selector of rule.required) {
            const matches = [...el.querySelectorAll(selector)].filter(visible);
            if (!matches.some((x) => x.textContent.trim()))
              add(
                rule,
                `Missing visible, nonempty context: ${selector}.`,
                el,
                selector,
                "visible nonempty context",
              );
          }
        if (rule.type === "no-clip") {
          const style = getComputedStyle(el);
          const clippedX =
            ["hidden", "clip"].includes(style.overflowX) &&
            el.scrollWidth > el.clientWidth + 1;
          const clippedY =
            ["hidden", "clip"].includes(style.overflowY) &&
            el.scrollHeight > el.clientHeight + 1;
          if (clippedX || clippedY)
            add(
              rule,
              "Content is clipped inside this element.",
              el,
              {
                scrollWidth: el.scrollWidth,
                clientWidth: el.clientWidth,
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight,
              },
              "no hidden overflow",
            );
        }
      }
  }
  return {
    findings,
    metrics: {
      viewportWidth: width,
      viewportHeight: innerHeight,
      pageHeight: document.documentElement.scrollHeight,
      evaluatedRules: evaluated,
      density,
    },
  };
}
