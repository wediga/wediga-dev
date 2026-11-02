"use client";

import { Fragment, useState, type CSSProperties } from "react";
import { ARCHIVED, STATUS_CLASS } from "@/lib/projectStatus";
import { safeHref } from "@/lib/url";
import type { PortfolioTile, TextField } from "@/lib/types";

// The texts an open tile shows below its row, in this order.
const DETAILS: { field: TextField; label: string }[] = [
  { field: "problem", label: "Problem" },
  { field: "solution", label: "Lösung" },
  { field: "learning", label: "Gelernt" },
  { field: "ending", label: "Warum es endete" },
];

// Cap the entrance stagger so late items in a long list do not wait seconds.
const LAST_REVEAL_STEP = 6;
// The heading and its label take the first two steps of the page.
const FIRST_TILE_STEP = 2;

const revealVar = (i: number) =>
  ({ "--reveal-i": String(Math.min(i, LAST_REVEAL_STEP)) }) as CSSProperties;

function Status({ tile }: { tile: PortfolioTile }) {
  const { label, className } = tile.archived
    ? ARCHIVED
    : { label: tile.status.label, className: STATUS_CLASS[tile.status.key] };

  return (
    <span className={`shrink-0 font-mono text-xs tracking-[0.04em] ${className}`}>
      {label}
    </span>
  );
}

function Technologies({ names }: { names: string[] }) {
  if (names.length === 0) return null;

  return (
    <span className="mt-5 flex flex-wrap gap-x-4 gap-y-2">
      {names.map((name) => (
        <span
          key={name}
          data-gen-dot
          className="gen-dot flex items-center gap-2 font-mono text-xs text-ink"
        >
          {name}
        </span>
      ))}
    </span>
  );
}

// Closed: name, status, description and tech stack. The whole tile is the
// button that opens its details.
function Tile({
  tile,
  index,
  open,
  onToggle,
}: {
  tile: PortfolioTile;
  index: number;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls={`details-${tile.id}`}
      className={`reveal flex h-full flex-col border-t pt-6 pb-8 text-left transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent/60 ${
        open ? "border-accent" : "border-line hover:border-muted-2"
      }`}
      style={revealVar(index + FIRST_TILE_STEP)}
    >
      <span className="flex w-full items-baseline justify-between gap-4">
        <span className="text-[1.2rem] font-semibold leading-tight tracking-[-0.01em] text-ink">
          {tile.texts.name}
        </span>
        <Status tile={tile} />
      </span>
      {tile.texts.description ? (
        <span className="mt-2 block text-pretty leading-snug text-accent">
          {tile.texts.description}
        </span>
      ) : null}
      <Technologies names={tile.technologies} />
    </button>
  );
}

// Open: the prose fields and the links, across the full width below the row.
function Details({ tile }: { tile: PortfolioTile }) {
  const demo = safeHref(tile.demo_url);
  const github = safeHref(tile.github_url);

  return (
    <div
      id={`details-${tile.id}`}
      className="col-span-full border-t border-line pt-6 pb-10"
    >
      <div className="grid max-w-none gap-6 text-pretty leading-relaxed text-ink/90 md:grid-cols-2">
        {DETAILS.map(({ field, label }) =>
          tile.texts[field] ? (
            <div key={field}>
              <p className="font-medium text-muted">{label}</p>
              <p className="mt-1 whitespace-pre-line">{tile.texts[field]}</p>
            </div>
          ) : null,
        )}
      </div>
      <div className="mt-6 flex gap-6">
        {demo ? (
          <a href={demo} className="gen-link text-sm" rel="noreferrer noopener">
            Demo
          </a>
        ) : null}
        {github ? (
          <a href={github} className="gen-link text-sm" rel="noreferrer noopener">
            GitHub
          </a>
        ) : null}
      </div>
    </div>
  );
}

// Three tiles per row on wide screens, one open at a time. The details follow
// their tile in the markup and span the full width, and the dense flow lets
// the rest of the row move up beside the open tile, so the details land below
// its row at every column count.
export function PortfolioTiles({ tiles }: { tiles: PortfolioTile[] }) {
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="mt-2 grid grid-flow-row-dense gap-x-10 md:grid-cols-2 lg:grid-cols-3">
      {tiles.map((tile, index) => (
        <Fragment key={tile.id}>
          <Tile
            tile={tile}
            index={index}
            open={openId === tile.id}
            onToggle={() => setOpenId(openId === tile.id ? null : tile.id)}
          />
          {openId === tile.id ? <Details tile={tile} /> : null}
        </Fragment>
      ))}
    </div>
  );
}
