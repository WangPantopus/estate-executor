/**
 * Static test data used across E2E tests.
 */

export const FIRM_DATA = {
  name: 'E2E Law Partners LLP',
  type: 'law_firm' as const,
};

export const MATTER_DATA = {
  decedentName: 'Jane E2E Doe',
  title: 'Estate of Jane E2E Doe',
  estateType: 'Probate — with Will',
  jurisdictionState: 'California',
  dateOfDeath: '2024-06-01',
  estimatedValue: '1500000',
  assetTypes: ['Real estate', 'Bank accounts', 'Investment / brokerage accounts'],
};

export const TASK_DATA = {
  title: 'E2E Test Task — Locate original will',
  description: 'Locate and secure the original signed will document.',
  phase: 'Immediate',
  priority: 'Critical',
};

export const STAKEHOLDER_DATA = {
  email: 'stakeholder-e2e@test.local',
  fullName: 'Sam Stakeholder',
  role: 'Beneficiary',
  relationship: 'Spouse',
};

export const DOCUMENT_DATA = {
  filename: 'test-will.pdf',
  mimeType: 'application/pdf',
  docType: 'Will',
};

export const DEADLINE_DATA = {
  title: 'E2E Court Filing Deadline',
  description: 'Must file petition within 30 days of appointment.',
  dueDate: new Date(Date.now() + 30 * 86_400_000).toISOString().slice(0, 10),
};

export const ASSET_DATA = {
  title: 'E2E Family Residence',
  assetType: 'Real estate',
  institution: 'Recorded in County',
  ownershipType: 'Individual',
  estimatedValue: '850000',
};
