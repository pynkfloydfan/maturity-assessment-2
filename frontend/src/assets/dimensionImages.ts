import governanceLeadership from "./dimensions/governance-leadership.png";
import riskAssessment from "./dimensions/risk-assessment-management.png";
import bcDrPlanning from "./dimensions/bc-dr-planning.png";
import processDependency from "./dimensions/process-dependency-mapping.png";
import itCyber from "./dimensions/it-cyber-resilience.png";
import crisisComms from "./dimensions/crisis-comms-incident-mgmt.png";
import thirdParty from "./dimensions/third-party-resilience.png";
import cultureHuman from "./dimensions/culture-human-factors.png";
import regulatory from "./dimensions/regulatory-compliance-resolvability.png";

export const dimensionImageByName: Record<string, string> = {
  "Governance & Leadership": governanceLeadership,
  "Risk Assessment & Management": riskAssessment,
  "BC & DR Planning": bcDrPlanning,
  "Process & Dependency Mapping": processDependency,
  "IT & Cyber Resilience": itCyber,
  "Crisis Comms & Incident Mgmt": crisisComms,
  "Third-Party Resilience": thirdParty,
  "Culture & Human Factors": cultureHuman,
  "Regulatory Compliance & Resolvability": regulatory,
};

export const dimensionImageByFilename: Record<string, string> = {
  "governance-leadership.png": governanceLeadership,
  "risk-assessment-management.png": riskAssessment,
  "bc-dr-planning.png": bcDrPlanning,
  "process-dependency-mapping.png": processDependency,
  "it-cyber-resilience.png": itCyber,
  "crisis-comms-incident-mgmt.png": crisisComms,
  "third-party-resilience.png": thirdParty,
  "culture-human-factors.png": cultureHuman,
  "regulatory-compliance-resolvability.png": regulatory,
};
