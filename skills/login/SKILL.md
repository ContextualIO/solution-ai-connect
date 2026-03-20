---
name: login
description: Start login for a config and wait for completion.
disable-model-invocation: true
argument-hint: [config-id]
---

# Contextual Login

Target: `$ARGUMENTS`

## Instructions

1. If `$ARGUMENTS` is empty, call `config_list` and ask the user which config should be used.
2. Call `setup_access` first if access is not ready.
3. Call `config_use` if the chosen config is not current.
4. Call `login_start` with the chosen config id.
5. Relay the verification code immediately.
6. Tell the user to confirm the same code in the browser window and approve it there.
7. Call `login_await` with a 90 second timeout.
8. If waiting times out, keep the job id and check again with `login_status`.

## Output

Return:

- config id
- verification code if available
- login status: completed, pending, or error
- the next command to retry
