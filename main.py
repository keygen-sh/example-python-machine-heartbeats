from uuid import getnode as get_mac
import threading
import signal
import requests
import json
import hashlib
import sys
import os

def to_error_message(errs):
  """
  Formats an array of error dicts into an error message string. Returns an error message.
  """

  return ', '.join(map(lambda e: f"{e['title']}: {e['detail']}", errs))

def validate_license_key_with_fingerprint(license_key, machine_fingerprint):
  """
  Validates a license key scoped to a machine fingerprint. Returns a validation code and the license's ID.
  """

  validation = requests.post(
    f"https://api.keygen.sh/v1/accounts/{os.environ['KEYGEN_ACCOUNT_ID']}/licenses/actions/validate-key",
    headers={
      'Content-Type': 'application/vnd.api+json',
      'Accept': 'application/vnd.api+json'
    },
    data=json.dumps({
      'meta': {
        'scope': { 'fingerprint': machine_fingerprint },
        'key': license_key
      }
    })
  ).json()

  license_id = None
  if 'data' in validation:
    data = validation['data']
    if data != None:
      license_id = data['id']

  if 'errors' in validation:
    errs = validation['errors']

    print(f'[keygen.validate_license_key_with_fingerprint] license_id={license_id} machine_fingerprint={machine_fingerprint} errors={to_error_message(errs)}',
          file=sys.stderr)

    return None, license_id

  validation_code = validation['meta']['code']

  print(f'[keygen.validate_license_key_with_fingerprint] validation_code={validation_code} license_id={license_id} machine_fingerprint={machine_fingerprint}')

  return validation_code, license_id

def activate_machine_for_license(license_id, machine_fingerprint):
  """
  Activates a machine for a license. Returns the activated machine's ID.
  """

  activation = requests.post(
    f"https://api.keygen.sh/v1/accounts/{os.environ['KEYGEN_ACCOUNT_ID']}/machines",
    headers={
      'Authorization': f"Bearer {os.environ['KEYGEN_ACTIVATION_TOKEN']}",
      'Content-Type': 'application/vnd.api+json',
      'Accept': 'application/vnd.api+json'
    },
    data=json.dumps({
      'data': {
        'type': 'machines',
        'attributes': {
          'fingerprint': machine_fingerprint
        },
        'relationships': {
          'license': {
            'data': { 'type': 'licenses', 'id': license_id }
          }
        }
      }
    })
  ).json()

  if 'errors' in activation:
    errs = activation['errors']

    print(f'[keygen.activate_machine_for_license] license_id={license_id} machine_fingerprint={machine_fingerprint} errors={to_error_message(errs)}',
          file=sys.stderr)

    return None

  machine_id = activation['data']['id']

  print(f'[keygen.activate_machine_for_license] license_id={license_id} machine_id={machine_id} machine_fingerprint={machine_fingerprint}')

  return machine_id

def deactivate_machine(machine_id):
  """
  Deactivates a machine. Returns a boolean indicating success or failure.
  """

  deactivation = requests.delete(
    f"https://api.keygen.sh/v1/accounts/{os.environ['KEYGEN_ACCOUNT_ID']}/machines/{machine_id}",
    headers={
      'Authorization': f"Bearer {os.environ['KEYGEN_ACTIVATION_TOKEN']}",
      'Accept': 'application/vnd.api+json'
    }
  )

  if deactivation.status_code != 204:
    data = deactivation.json()
    errs = data['errors']

    print(f'[keygen.deactivate_machine] machine_id={machine_id} errors={to_error_message(errs)}',
          file=sys.stderr)

    return False

  print(f'[keygen.deactivate_machine] machine_id={machine_id}')

  return True

def deactivate_machine_on_exit(machine_id):
  """
  Deactivates a machine on exit signal. Exits program with exit code indicating deactivation success or failure.
  """

  ok = deactivate_machine(machine_fingerprint)
  if ok:
    sys.exit(0)
  else:
    sys.exit(1)

def ping_heartbeat_for_machine(machine_id):
  """
  Performs a hearbeat ping for a machine. Returns a boolean indicating success or failure.
  """

  ping = requests.post(
    f"https://api.keygen.sh/v1/accounts/{os.environ['KEYGEN_ACCOUNT_ID']}/machines/{machine_id}/actions/ping-heartbeat",
    headers={
      'Authorization': f"Bearer {os.environ['KEYGEN_ACTIVATION_TOKEN']}",
      'Accept': 'application/vnd.api+json'
    }
  ).json()

  if 'errors' in ping:
    errs = ping['errors']

    print(f'[keygen.ping_heartbeat_for_machine] machine_id={machine_id} errors={to_error_message(errs)}',
          file=sys.stderr)

    return False

  print(f'[keygen.ping_heartbeat_for_machine] machine_id={machine_id}')

  return True

def maintain_hearbeat_for_machine(machine_id):
  """
  Performs minutely hearbeat pings for a machine on a loop.
  """

  timer = threading.Timer(60.0, lambda: maintain_hearbeat_for_machine(machine_id))

  ok = ping_heartbeat_for_machine(machine_id)
  if not ok:
    sys.exit(1)

  timer.start()

# Fingerprint the current device and get the license key
machine_fingerprint = hashlib.sha256(str(get_mac()).encode('utf-8')).hexdigest()
license_key = sys.argv[1]

# Validate the license key scoped to the current machine fingerprint
validation_code, license_id = validate_license_key_with_fingerprint(license_key, machine_fingerprint)
if validation_code == 'NOT_FOUND':
  sys.exit(1)

# Attempt to activate the machine if it's not already activated
activation_is_required = validation_code == 'NO_MACHINE' or \
                         validation_code == 'NO_MACHINES' or \
                         validation_code == 'FINGERPRINT_SCOPE_MISMATCH'
if activation_is_required:
  machine_id = activate_machine_for_license(license_id, machine_fingerprint)
  if machine_id == None:
    sys.exit(1)

# Attempt to deactivate machine on process exit
signal.signal(signal.SIGINT, lambda _s, _f: deactivate_machine_on_exit(machine_fingerprint))

# Start a heartbeat ping loop
maintain_hearbeat_for_machine(machine_fingerprint)
