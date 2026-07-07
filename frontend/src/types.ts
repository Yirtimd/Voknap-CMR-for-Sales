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
  role?: string | null;
  actions?: {
    call: boolean;
    email: boolean;
    more: boolean;
  };
  created_at?: string;
};

export type Owner = {
  id: string | null;
  name: string | null;
  avatar_url: string | null;
  initials: string | null;
};

export type Company = {
  id: string;
  name: string;
  website: string | null;
  industry: string | null;
  description: string | null;
  status: string;
  status_label?: string | null;
  company_type?: string | null;
  health_score?: number | null;
  client_since?: string | null;
  source?: string | null;
  owner?: Owner | null;
  next_action_id?: string | null;
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
  probability?: number | null;
  expected_close_date?: string | null;
  expected_next_event?: string | null;
  next_step?: string | null;
  risk_level?: string | null;
  forecast_category?: string | null;
  owner_id?: string | null;
  next_action_id?: string | null;
  age_days?: number | null;
  created_at?: string;
};

export type Task = {
  id: string;
  company_id: string;
  title: string;
  description: string | null;
  deal_id: string | null;
  status: string;
  priority: string;
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
  company_id?: string | null;
  deal_id?: string | null;
  file_id?: string | null;
  title: string;
  source_type: string;
  visibility?: string;
  status: string;
  created_at: string;
  chunks_count: number;
};

export type KnowledgeSearchResult = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_scope?: string;
  company_id?: string | null;
  deal_id?: string | null;
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

export type CompanyCopilot = {
  company_id: string;
  summary: string;
  next_best_action: string;
  deal_risk: {
    level: string;
    score: number;
    reason: string;
  };
  follow_up_draft: string;
  meeting_prep: string;
  insight: Record<string, unknown>;
  actions: AgentAction[];
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
  channel: string | null;
  title: string;
  description: string | null;
  created_by: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type CompanyHealth = {
  score: number | null;
  label: string | null;
  trend: string | null;
  risk_level: string | null;
  success_chance: number | null;
  success_chance_delta: number | null;
  ai_recommendations: Array<{
    type?: string;
    title: string;
    description?: string;
  }>;
};

export type CompanyFile = {
  id: string;
  name: string;
  file_type: string | null;
  mime_type: string | null;
  file_size: number | null;
  uploaded_at: string;
  download_url: string;
};

export type WorkspaceKnowledgeDocument = {
  id: string;
  title: string;
  source_type: string;
  visibility: string;
  company_id: string | null;
  deal_id: string | null;
  file_id: string | null;
  created_at: string;
  chunks_count: number;
};

export type WorkspaceActivity = {
  id: string;
  type: string;
  activity_type: string;
  activity_icon: string;
  channel: string | null;
  title: string;
  description: string | null;
  author_name: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type NextAction = {
  id: string;
  company_id: string;
  deal_id: string | null;
  contact_id: string | null;
  assigned_to_id: string | null;
  title: string;
  description: string | null;
  source: string;
  status: string;
  priority: string;
  due_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type CompanyWorkspace = {
  company: Company;
  overview: Record<string, number | string | null>;
  health: CompanyHealth;
  next_action: NextAction | null;
  contacts: Contact[];
  deals: Deal[];
  tasks: Task[];
  activities: WorkspaceActivity[];
  files: CompanyFile[];
  knowledge_documents: WorkspaceKnowledgeDocument[];
  ai_summary: string;
  ai_insights: string[];
};
