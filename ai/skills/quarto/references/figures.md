# Figures in Quarto

Use the project’s plotting stack and design system. For detailed Matplotlib geometry, annotation, or layout work, use the `matplotlib` skill alongside this reference. Figure architecture and reusable helpers should serve the project; a small chart does not require a separate module or a shared organization library.

## Figure chunks

Keep the label, caption, dimensions, and plotted units explicit when they matter:

````markdown
```{python}
#| label: fig-observations
#| fig-cap: "Observed values by period."
#| fig-width: 6
#| fig-height: 3

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 3))
ax.plot(periods, values)
ax.set_xlabel("Period")
ax.set_ylabel("Observed value")
plt.show()
```
````

The caption must describe the actual data. If a figure function is reused, keep its inputs explicit and let its caller decide how the figure is displayed, saved, and closed. In a standalone save path, save before closing. Keep private data and synthetic examples distinguishable.

## Layout and dimensions

Distinguish the plotting canvas, saved image bounds, and document placement width. Tight bounding boxes can change saved dimensions; annotations outside the axes can expand those bounds unexpectedly. Inspect both the generated figure and its document placement before changing unrelated margins or scaling every image.

Check coordinate transforms before moving annotations. Use axes coordinates for axes-relative placement and data coordinates for data-relative marks. Clip only where clipping preserves the intended information; otherwise allow room for the label. Do not hide useful annotations merely to make a bounding box smaller.

## Visual review

Inspect the rendered output at a readable scale. Check labels, contrast against the actual background, legends, units, date axes, chart truthfulness, clipped edges, and consistency across a figure series. A screenshot or successful save is evidence only after its content has been inspected. Re-render the affected figure and document after a relevant correction.

Read [Quarto’s figure guide](https://quarto.org/docs/authoring/figures.html) for labels, captions, layouts, and format-specific options.
