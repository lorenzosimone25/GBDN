"""Visualization helpers for paper figures."""

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import torch
from matplotlib.colors import hsv_to_rgb

FIGURES_DIR = Path(__file__).resolve().parents[2] / "figures" / "draft"

# Paper style defaults
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#fafafa",
    "font.size": 10,
})


def ensure_figures_dir() -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIGURES_DIR


def save_figure(name: str, dpi: int = 200, bbox_inches: str = "tight") -> Path:
    ensure_figures_dir()
    stem = Path(name).stem
    pdf_path = FIGURES_DIR / f"{stem}.pdf"
    png_path = FIGURES_DIR / f"{stem}.png"
    plt.savefig(pdf_path, dpi=dpi, bbox_inches=bbox_inches)
    plt.savefig(png_path, dpi=dpi, bbox_inches=bbox_inches)
    return pdf_path


def _to_numpy(signal):
    if isinstance(signal, torch.Tensor):
        if signal.is_complex():
            return signal.detach().cpu().numpy()
        return signal.detach().cpu().numpy()
    return np.asarray(signal)


def domain_color(f: np.ndarray, mag_mode: str = "log", gamma: float = 0.35) -> np.ndarray:
    """Domain coloring for complex function samples (hue=phase, value=magnitude)."""
    arg = np.angle(f)
    hue = (arg + np.pi) / (2 * np.pi)
    sat = np.ones_like(hue)
    if mag_mode == "flat":
        val = np.ones_like(hue) * 0.98
    else:
        m = np.log1p(np.abs(f))
        m = m / (m.max() + 1e-12)
        val = 0.2 + 0.8 * (m ** gamma)
    return hsv_to_rgb(np.stack([hue, sat, val], axis=-1))


def plot_blaschke_disk(
    alpha_re: float,
    alpha_im: float,
    resolution: int = 200,
    ax: Optional[plt.Axes] = None,
    title: str = r"$B_\alpha(z)$ on unit disk",
):
    """Domain-colored Blaschke factor on the complex unit disk."""
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))

    r = np.linspace(0, 1, resolution)
    t = np.linspace(0, 2 * np.pi, resolution)
    R, T = np.meshgrid(r, t)
    z = R * np.exp(1j * T)
    alpha = alpha_re + 1j * alpha_im
    B = (z - alpha) / (1.0 - np.conj(alpha) * z)
    rgb = domain_color(B, mag_mode="flat")

    ax.imshow(
        rgb, extent=[-1, 1, -1, 1], origin="lower",
        interpolation="bilinear",
    )
    circle = plt.Circle((0, 0), 1, fill=False, color="white", linewidth=1.2, alpha=0.8)
    ax.add_patch(circle)
    ax.scatter([alpha_re], [alpha_im], c="white", edgecolors="black", s=60, zorder=5)
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xlabel(r"$\mathrm{Re}(z)$")
    ax.set_ylabel(r"$\mathrm{Im}(z)$")
    return ax


def plot_cayley_spectrum(
    evals: torch.Tensor,
    ax: Optional[plt.Axes] = None,
    title: str = "Cayley image of graph spectrum",
):
    """Plot Laplacian eigenvalues on [0,2] and their Cayley images on the circle."""
    from gbdn.spectral import cayley_map

    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))

    lam = evals.detach().cpu().float()
    zeta = cayley_map(lam)
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(theta), np.sin(theta), "k--", alpha=0.25, linewidth=1)
    ax.scatter(zeta.real.cpu(), zeta.imag.cpu(), c=lam.numpy(), cmap="viridis", s=12, zorder=3)
    ax.set_aspect("equal")
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_title(title)
    ax.set_xlabel(r"$\mathrm{Re}(\phi(\lambda))$")
    ax.set_ylabel(r"$\mathrm{Im}(\phi(\lambda))$")
    return ax


def plot_spectral_response(
    evals: torch.Tensor,
    response: torch.Tensor,
    idx_markers: Optional[List[int]] = None,
    ax: Optional[plt.Axes] = None,
    title: str = r"$|g(\lambda)|$ on Laplacian spectrum",
):
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 3.5))

    lam = evals.detach().cpu().numpy()
    resp = response.detach().cpu().numpy()
    ax.plot(lam, resp, color="#2c5aa0", linewidth=1.5)
    ax.fill_between(lam, 0, resp, alpha=0.15, color="#2c5aa0")
    if idx_markers:
        for k in idx_markers:
            if k < len(lam):
                ax.axvline(lam[k], color="crimson", linestyle="--", alpha=0.6, linewidth=1)
    ax.set_xlim(0, 2)
    ax.set_xlabel(r"Eigenvalue $\lambda$")
    ax.set_ylabel(r"$|g(\lambda)|$")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    return ax


def plot_learned_roots(
    alphas: Sequence,
    ax: Optional[plt.Axes] = None,
    title: str = "Learned Blaschke roots",
    colors: Optional[List[str]] = None,
):
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))

    theta = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(theta), np.sin(theta), color="#888888", linestyle="--", alpha=0.5, linewidth=1)

    flat = []
    for roots in alphas:
        if torch.is_tensor(roots):
            flat.extend(
                [(root.real.item(), root.imag.item()) for root in roots.reshape(-1)]
            )
        elif (
            isinstance(roots, (list, tuple))
            and len(roots) > 0
            and isinstance(roots[0], (list, tuple))
        ):
            flat.extend(roots)
        else:
            flat.append(roots)

    cmap = colors or plt.cm.tab10.colors
    for i, item in enumerate(flat):
        re, im = item[0], item[1]
        ax.scatter([re], [im], s=90, zorder=3, color=cmap[i % len(cmap)], edgecolors="black", linewidths=0.5,
                   label=f"root {i}")

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_aspect("equal")
    ax.axhline(0, color="gray", linewidth=0.4)
    ax.axvline(0, color="gray", linewidth=0.4)
    ax.set_xlabel(r"$\mathrm{Re}(\alpha)$")
    ax.set_ylabel(r"$\mathrm{Im}(\alpha)$")
    ax.set_title(title)
    if len(flat) <= 10:
        ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
    return ax


def _signal_values(signal, grid_size: int) -> np.ndarray:
    vals = _to_numpy(signal)
    if np.iscomplexobj(vals):
        vals = np.abs(vals)
    if vals.ndim > 1:
        vals = vals[:, 0]
    return vals.reshape(grid_size, grid_size)


def plot_grid_with_edges(
    G: nx.Graph,
    signal: Union[torch.Tensor, np.ndarray],
    grid_size: int,
    title: str = "",
    ax: Optional[plt.Axes] = None,
    cmap: str = "coolwarm",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
):
    """Grid heatmap with graph edges overlaid (paper-quality)."""
    grid = _signal_values(signal, grid_size)
    if vmin is None:
        vmin = grid.min()
    if vmax is None:
        vmax = grid.max()

    if ax is None:
        _, ax = plt.subplots(figsize=(4.2, 4.2))

    im = ax.imshow(grid, cmap=cmap, origin="lower", vmin=vmin, vmax=vmax, interpolation="bilinear")

    # Draw edges in grid coordinates
    pos = {(i, j): (j, i) for i in range(grid_size) for j in range(grid_size)}
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        ax.plot([x0, x1], [y0, y1], color="#333333", alpha=0.25, linewidth=0.6, zorder=2)

    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return ax, im


def plot_grid_signal(signal, grid_size, title="", ax=None, cmap="coolwarm"):
    return plot_grid_with_edges(
        nx.grid_2d_graph(grid_size, grid_size), signal, grid_size, title, ax, cmap
    )[0]


def plot_grid_panel(
    G: nx.Graph,
    signals: Dict[str, Union[torch.Tensor, np.ndarray]],
    grid_size: int,
    suptitle: str = "",
    cmaps: Optional[Dict[str, str]] = None,
):
    """Multi-panel grid figure with shared color scale per row or global."""
    n = len(signals)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4))
    if n == 1:
        axes = [axes]

    all_vals = []
    for s in signals.values():
        all_vals.append(_signal_values(s, grid_size))
    vmin = min(v.min() for v in all_vals)
    vmax = max(v.max() for v in all_vals)

    cmaps = cmaps or {}
    for ax, (name, sig) in zip(axes, signals.items()):
        cm = cmaps.get(name, "coolwarm" if "high" in name else "coolwarm")
        if "high" in name:
            cm = "seismic"
        if "mix" in name:
            cm = "PuOr"
        if "residual" in name or "peel" in name:
            cm = "magma"
        plot_grid_with_edges(G, sig, grid_size, title=name, ax=ax, cmap=cm, vmin=vmin, vmax=vmax)

    if suptitle:
        fig.suptitle(suptitle, fontsize=12, y=1.02)
    fig.tight_layout()
    return fig


def eigenmode_energy(h: torch.Tensor, evecs: torch.Tensor) -> np.ndarray:
    h_np = _to_numpy(h)
    evecs_np = evecs.detach().cpu().numpy()
    if h_np.ndim == 1:
        h_np = h_np[:, None]
    energies = []
    for c in range(h_np.shape[1]):
        coeff = evecs_np.T @ h_np[:, c]
        energies.append(np.abs(coeff) ** 2)
    return np.sum(energies, axis=0)


def plot_energy_bars(energies_before, energies_after, k_target=None, top_k=20, ax=None, title="Eigenmode energy"):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))
    n = min(top_k, len(energies_before))
    x = np.arange(n)
    w = 0.35
    ax.bar(x - w / 2, energies_before[:n], w, label="before", color="#4c72b0", alpha=0.85)
    ax.bar(x + w / 2, energies_after[:n], w, label="after", color="#dd8452", alpha=0.85)
    if k_target is not None and k_target < n:
        ax.axvline(k_target, color="crimson", linestyle="--", alpha=0.7, label="target")
    ax.set_xlabel("Eigenmode index")
    ax.set_ylabel("Energy")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.2)
    return ax


def plot_energy_per_layer(layer_energies: List[np.ndarray], idx_target: int, top_k: int = 20, ax=None):
    """Stacked line plot of target-mode energy across peel layers."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    targets = [e[idx_target] for e in layer_energies]
    totals = [e.sum() for e in layer_energies]
    layers = np.arange(len(layer_energies))
    ax.plot(layers, targets, "o-", color="crimson", label=f"mode {idx_target} energy")
    ax.plot(layers, totals, "s--", color="#4c72b0", alpha=0.7, label="total energy")
    ax.set_xlabel("Peel step")
    ax.set_ylabel("Energy")
    ax.set_title("Spectral energy through unwinding")
    ax.legend()
    ax.grid(True, alpha=0.25)
    return ax


def plot_layer_filmstrip(
    G: nx.Graph,
    tensors: List[Union[torch.Tensor, np.ndarray]],
    grid_size: int,
    labels: Optional[List[str]] = None,
    cmap: str = "coolwarm",
    suptitle: str = "Layer-wise unwinding",
):
    n = len(tensors)
    fig, axes = plt.subplots(1, n, figsize=(3.8 * n, 4))
    if n == 1:
        axes = [axes]
    labels = labels or [f"step {i}" for i in range(n)]
    vals = [_signal_values(t, grid_size) for t in tensors]
    vmin, vmax = min(v.min() for v in vals), max(v.max() for v in vals)
    for ax, t, lab in zip(axes, tensors, labels):
        plot_grid_with_edges(G, t, grid_size, title=lab, ax=ax, cmap=cmap, vmin=vmin, vmax=vmax)
    if suptitle:
        fig.suptitle(suptitle, fontsize=12, y=1.02)
    fig.tight_layout()
    return fig


def plot_sphere_wireframe(
    points: np.ndarray,
    signal: Union[torch.Tensor, np.ndarray],
    edges: Optional[List[Tuple[int, int]]] = None,
    ax=None,
    title: str = "",
    cmap: str = "coolwarm",
    edge_color: str = "#aaaaaa",
    edge_alpha: float = 0.35,
):
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    vals = _to_numpy(signal)
    if np.iscomplexobj(vals):
        vals = np.abs(vals)
    if vals.ndim > 1:
        vals = vals[:, 0]

    if ax is None:
        fig = plt.figure(figsize=(6, 6), facecolor="white")
        ax = fig.add_subplot(111, projection="3d", facecolor="#fafafa")

    if edges:
        for i, j in edges:
            xs = [points[i, 0], points[j, 0]]
            ys = [points[i, 1], points[j, 1]]
            zs = [points[i, 2], points[j, 2]]
            ax.plot(xs, ys, zs, color=edge_color, alpha=edge_alpha, linewidth=0.5)

    sc = ax.scatter(
        points[:, 0], points[:, 1], points[:, 2],
        c=vals, cmap=cmap, s=28, depthshade=True, edgecolors="none",
    )
    ax.set_title(title, pad=10)
    ax.set_axis_off()
    plt.colorbar(sc, ax=ax, shrink=0.55, pad=0.08)
    return ax


def plot_sphere_signal(points, signal, ax=None, title="", cmap="coolwarm"):
    return plot_sphere_wireframe(points, signal, ax=ax, title=title, cmap=cmap)


def plot_norm_ratio(ratios: dict, ax=None, title=r"$\|h^{(\ell)}\| / \|h^{(0)}\|$ vs layer"):
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for name, values in ratios.items():
        ax.plot(np.arange(len(values)), values, marker="o", linewidth=2, label=name)
    ax.set_xlabel("Layer")
    ax.set_ylabel("Norm ratio")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax


def plot_dirichlet_energy(energies: dict, ax=None, title="Dirichlet energy $h^\\top L h$"):
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for name, values in energies.items():
        ax.plot(np.arange(len(values)), values, marker="s", label=name)
    ax.set_xlabel("Layer")
    ax.set_ylabel("Dirichlet energy")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax
