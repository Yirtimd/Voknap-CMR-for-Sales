export type Tenant = {
  id: string;
  name: string;
  slug: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  tenants: Tenant[];
};

export type Contact = {
  id: string;
  company_id: string;
  name: string;
  phone: string | null;
  email: string | null;
  company_name: string | null;
  created_at?: string;
};

export type Company = {
  id: string;
  name: string;
  website: string | null;
  industry: string | null;
  description: string | null;
  created_at: string;
};

export type Lead = {
  id: string;
  company_id: string;
  title: string;
  source: string | null;
  status: string;
  contact_id: string | null;
  created_at?: string;
};

export type PipelineStage = {
  id: string;
  name: string;
  sort_order: number;
};

export type Pipeline = {
  id: string;
  name: string;
  stages: PipelineStage[];
  created_at?: string;
};

export type Deal = {
  id: string;
  company_id: string;
  title: string;
  amount: number | null;
  status: string;
  lead_id: string | null;
  stage_id: string;
  created_at?: string;
};

export type Task = {
  id: string;
  company_id: string;
  title: string;
  description: string | null;
  deal_id: string | null;
  due_at: string | null;
  done_at: string | null;
  created_at?: string;
};

export type Note = {
  id: string;
  company_id: string;
  text: string;
  lead_id: string | null;
  deal_id: string | null;
  author_id?: string;
  created_at?: string;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  source_type: string;
  status: string;
  created_at: string;
  chunks_count: number;
};

export type KnowledgeSearchResult = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  text: string;
  score: number;
  chunk_index: number;
};

export type KnowledgeAskResponse = {
  answer: string;
  citations: KnowledgeSearchResult[];
};

export type AgentAction = {
  id: string;
  action_type: string;
  status: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  created_at: string;
  confirmed_at: string | null;
};

export type AgentChatResponse = {
  answer: string;
  actions: AgentAction[];
  sources: Record<string, unknown>[];
};

export type AgentHistoryMessage = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

export type ConnectorDefinition = {
  code: string;
  title: string;
  description: string;
  status: string;
};

export type ConnectorAccount = {
  id: string;
  connector_code: string;
  title: string;
  status: string;
  settings: Record<string, unknown>;
  last_sync_at: string | null;
  created_at: string;
};

export type ConnectorSyncRun = {
  id: string;
  account_id: string;
  direction: string;
  status: string;
  created_count: number;
  updated_count: number;
  failed_count: number;
  message: string | null;
  created_at: string;
};

export type CsvExportResponse = {
  filename: string;
  csv_text: string;
};

export type CompanyTemplate = {
  code: string;
  title: string;
  description: string;
  pipeline_name: string;
  stages: string[];
  lead_sources: string[];
  ai_instruction: string;
};

export type AppliedTemplate = {
  id: string;
  template_code: string;
  template_title: string;
  status: string;
  result: Record<string, unknown>;
  created_at: string;
};

export type ProductionOverview = {
  tenant_id: string;
  counts: Record<string, number>;
  plan: Record<string, unknown>;
  flags: Record<string, unknown>[];
};

export type AuditLog = {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type FeatureFlag = {
  id: string;
  code: string;
  title: string;
  enabled: boolean;
  created_at: string;
};

export type TenantPlan = {
  id: string;
  plan_code: string;
  users_limit: number;
  leads_limit: number;
  documents_limit: number;
  ai_requests_limit: number;
  created_at: string;
};

export type TenantExport = {
  filename: string;
  data: Record<string, unknown>;
};

export type Activity = {
  id: string;
  tenant_id: string;
  company_id: string | null;
  contact_id: string | null;
  deal_id: string | null;
  type: string;
  title: string;
  description: string | null;
  created_by: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type CompanyWorkspace = {
  company: Company;
  overview: Record<string, number>;
  contacts: Contact[];
  deals: Deal[];
  tasks: Task[];
  activities: Array<Record<string, unknown>>;
  ai_summary: string;
  ai_insights: string[];
};
