# Dyrne

> [!NOTE]
> Dyrne is currently in the early planning/implementation phase.

## Concept

Dyrne will act as a local, offline mirror for your secret stores and password managers.

### Components

* secret-store - The core of Dyrne. Handles storing secrets and responding to requests and, if necessary, routing requests to other components.
* secret-fetcher - Handles fetching secrets from external services (Bitwarden Secrets Manager, 1Password, ...). Should also handle creating secrets? Probably needs a better name.
* secret-generator - Generates secrets on demand according to user-defined complexity rules (uppers, lowers, numbers, specials, ...).

### Feature Highlights

* Pluggability
  * Easily extensible with custom modules (name TBD - adaptors, plugins, transformers, ... ?)
  * The plan is currently to allow for pluggability of the secret-fetcher module, allowing for theoretically infinite integrations with external secret/password management services.
* On-demand secret generation
  * If a queried secret does not exist, it should be generated, stored, and returned to the user.
  * The user should not have to care whether a secret is pre-existing or not.
