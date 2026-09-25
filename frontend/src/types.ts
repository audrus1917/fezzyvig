export interface User {
  id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  created_at: string;
}

export interface EmployerVacancy {
  id: number;
  external_id: string;
  title: string;
  company: string;
  area_name: string | null;
  employment_form_name: string | null;
  vacancy_type_name: string | null;
  url: string;
  description: string;
  data: Record<string, unknown>;
  created_at: string | null;
  published_at: string | null;
  expires_at: string | null;
  synced_at: string;
}
