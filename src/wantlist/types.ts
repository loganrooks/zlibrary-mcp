export type Source = 'libgen' | 'zlibrary' | 'annas';
export interface Want {
  item_id: string;
  title: string;
  author?: string;
  year?: number;
  language?: string;
  formats?: string[];
  mode: 'any' | 'exact';
  volume?: number;
  translator?: string;
  editor?: string;
  notes?: string;
  edition_note?: string;
  extra: Record<string, unknown>;
  line: number;
  warnings: string[];
  duplicate?: string;
}
export interface Settings {
  sources: Source[];
  output_dir: string;
  mode?: 'any' | 'exact';
  formats?: string[];
  language?: string;
  reserve: number;
  max_downloads?: number;
  probe: boolean;
}
export type ItemState =
  | 'pending'
  | 'fetched'
  | 'have'
  | 'needs_choice'
  | 'waiting_quota'
  | 'retry_later'
  | 'not_found'
  | 'failed'
  | 'skipped'
  | 'dropped'
  | 'duplicate';
export interface Candidate {
  ref?: string;
  source: Source;
  identifiers: Record<string, string>;
  title: string;
  author?: string;
  year?: number;
  language?: string;
  format?: string;
  quality?: number;
  pages?: number;
  publisher?: string;
  series?: string;
  description?: string;
  translator?: string;
  edition?: string;
  evidence?: Record<string, any>;
  score?: number;
  author_match?: string;
  author_alt?: boolean;
  orientation?: string;
  volume_status?: string;
  derivative?: boolean;
  class?: string;
  checks?: Record<string, string>;
  missing?: string[];
  conflicts?: string[];
}
export interface Item {
  line: number;
  want: Want;
  mode: string;
  state: ItemState;
  reason?: string;
  why_chosen?: string;
  candidate?: Candidate;
  options?: Candidate[];
  record?: string;
  path?: string;
  sha256?: string;
  edition_check?: any;
  counts: { searches: number; details: number; downloads: number };
  history: { at: string; state: ItemState; reason?: string }[];
  choice?: string;
  dry_run?: boolean;
}
export interface ListState {
  state_version: 1;
  list: { path: string; sha256: string; parsed_at: string };
  settings: Settings;
  run: {
    pid: number;
    started_at: string;
    updated_at: string;
    status: string;
    stop_reason?: string;
  };
  quota?: { source: string; remaining?: number; basis: string; as_of: string };
  items: Record<string, Item>;
  edition_cache: Record<string, any>;
}
export interface RunOptions {
  path?: string;
  items?: (string | Record<string, any>)[];
  output_dir?: string;
  state?: string;
  sources?: Source[];
  mode?: 'any' | 'exact';
  formats?: string[];
  language?: string;
  reserve?: number;
  max_downloads?: number;
  max_minutes?: number;
  probe?: boolean;
  dry_run?: boolean;
  retry_not_found?: boolean;
  retry_failed?: boolean;
  redo?: string[];
  choices?: Record<string, string>;
  signal?: AbortSignal;
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
}
