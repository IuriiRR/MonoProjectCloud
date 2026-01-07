import React from 'react';
import { Users } from 'lucide-react';
import type { FamilyMemberInfo } from '../services/api';

type Props = {
  members: FamilyMemberInfo[];
  selectedUserIds: string[];
  onChangeSelectedUserIds: (next: string[]) => void;
  disabled?: boolean;
  compact?: boolean;
};

function uniq(xs: string[]) {
  return Array.from(new Set(xs.filter(Boolean)));
}

export default function FamilyMemberSelector({
  members,
  selectedUserIds,
  onChangeSelectedUserIds,
  disabled,
  compact,
}: Props) {
  const normalizedMembers = (members || []).filter((m) => m?.user_id);
  if (normalizedMembers.length === 0) return null;

  const selected = new Set(selectedUserIds || []);

  const toggle = (uid: string) => {
    const next = new Set(selected);
    if (next.has(uid)) next.delete(uid);
    else next.add(uid);
    onChangeSelectedUserIds(uniq(Array.from(next)));
  };

  return (
    <div className={compact ? 'flex items-center gap-2' : 'space-y-2'}>
      <div className="flex items-center gap-2 text-xs text-zinc-400">
        <Users size={12} />
        <span>Family</span>
      </div>
      <div className={compact ? 'flex flex-wrap gap-3' : 'space-y-2'}>
        {normalizedMembers.map((m) => {
          const uid = m.user_id;
          const label = m.username ? `${m.username}` : `${uid.slice(0, 6)}…`;
          const isChecked = selected.has(uid);
          return (
            <label
              key={uid}
              className={`flex items-center gap-2 select-none ${disabled ? 'opacity-50 cursor-default' : 'cursor-pointer'}`}
            >
              <input
                type="checkbox"
                checked={isChecked}
                disabled={disabled}
                onChange={() => toggle(uid)}
                className="h-3 w-3 accent-white rounded-sm"
                aria-label={`Include ${label}`}
              />
              <span className="text-xs text-zinc-400 hover:text-white transition-colors">
                {label}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

