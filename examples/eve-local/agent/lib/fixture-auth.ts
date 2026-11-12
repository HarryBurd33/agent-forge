import { timingSafeEqual } from "node:crypto";
import { extractBearerToken, type AuthFn } from "eve/channels/auth";

export const fixtureAuth: AuthFn<Request> = (request) => {
  const configured = process.env.AGENT_FORGE_FIXTURE_TOKEN;
  const token = extractBearerToken(request.headers.get("authorization"));
  if (!configured || !token) return null;

  const expected = Buffer.from(configured);
  const supplied = Buffer.from(token);
  if (expected.length !== supplied.length || !timingSafeEqual(expected, supplied)) return null;

  return {
    attributes: {},
    authenticator: "fixture",
    principalId: "local-fixture-runner",
    principalType: "service",
  };
};
