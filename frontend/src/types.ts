export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface EmployerVacancy {
  id: number;
  external_id: string;
  title: string;
  company: string;
  url: string;
  description: string;
  published_at: string | null;
  synced_at: string;
}

export interface EmployerSyncResult {
  synced: number;
}
