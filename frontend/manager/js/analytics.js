import { api } from "../../shared/utils.js";


export async function loadManagerAnalytics() {
  return api("/api/v2/manager/live");
}
