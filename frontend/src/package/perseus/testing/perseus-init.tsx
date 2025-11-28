// perseus-init.ts
import { registerAllWidgetsForTesting } from "../src/util/register-all-widgets-for-testing";
import { setDependencies,  } from "../src/dependencies";
import { storybookTestDependencies } from "./test-dependencies";

// Initialize Perseus
registerAllWidgetsForTesting();
setDependencies(storybookTestDependencies);