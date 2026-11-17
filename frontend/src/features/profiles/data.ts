import { api } from "../../shared/api";
import { errorMessage, type FormDefinition, type Profile } from "./model";

export async function loadForms(): Promise<FormDefinition[]> {
  const forms: FormDefinition[] = [];
  let total = 1;
  while (forms.length < total) {
    const { data, error } = await api.GET("/api/v1/forms", {
      params: { query: { limit: 200, offset: forms.length } },
    });
    if (error) throw new Error(errorMessage(error.error.code));
    forms.push(...data.data);
    total = data.pagination.total;
    if (!data.data.length) break;
  }
  return forms;
}

export async function loadProfiles(): Promise<Profile[]> {
  const profiles: Profile[] = [];
  let total = 1;
  while (profiles.length < total) {
    const { data, error } = await api.GET("/api/v1/profiles", {
      params: { query: { limit: 200, offset: profiles.length } },
    });
    if (error) throw new Error(errorMessage(error.error.code));
    profiles.push(...data.data);
    total = data.pagination.total;
    if (!data.data.length) break;
  }
  return profiles;
}
