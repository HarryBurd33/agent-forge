import { eveChannel } from "eve/channels/eve";
import { fixtureAuth } from "../lib/fixture-auth.js";

export default eveChannel({ auth: fixtureAuth });
