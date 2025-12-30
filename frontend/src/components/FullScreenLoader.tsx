import React from 'react';

type FullScreenLoaderProps = {
  label?: string;
};

export default function FullScreenLoader({ label = 'Loading…' }: FullScreenLoaderProps) {
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center px-6">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <div className="w-14 h-14 rounded-2xl bg-black border border-white/10 flex items-center justify-center">
            <span className="text-2xl font-black tracking-tight">m</span>
          </div>
          <div
            className="absolute -inset-2 rounded-3xl border-2 border-white/10 border-t-white/80 animate-spin"
            aria-hidden="true"
          />
        </div>

        <div className="text-sm text-zinc-400 text-center">{label}</div>
      </div>
    </div>
  );
}

