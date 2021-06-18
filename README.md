# Example Machine Activation Heartbeats

This is an example of a typical node-locked machine activation flow written
in Python, utilizing a machine hearbeat monitor to automatically deactivate
the machine in the event that the normal deactivation procedure fails.

## Running the example

First up, configure a few environment variables:

```bash
# A Keygen activation token for the given license. You can generate an
# activation token per-license via the API or your admin dashboard.
export KEYGEN_ACTIVATION_TOKEN="A_KEYGEN_ACTIVATION_TOKEN"

# Your Keygen account ID. Find yours at https://app.keygen.sh/settings.
export KEYGEN_ACCOUNT_ID="YOUR_KEYGEN_ACCOUNT_ID"
```

You can either run each line above within your terminal session before
starting the app, or you can add the above contents to your `~/.bashrc`
file and then run `source ~/.bashrc` after saving the file.

Next, install dependencies with [`pip`](https://packaging.python.org/):

```
pip install -r requirements.txt
```

To perform a machine activation, run the program with a license key:

```
python main.py some-license-key-here
```

The script will use a SHA256 hash of your device's MAC address for the
machine's fingerprint during activation. Upon activation, a heartbeat
monitor will be started for the activated machine.

If you **exit** the process, the machine will be deactivated.

If you **kill** the process, the heartbeat monitor will automatically
deactivate the machine after the heartbeat window has been reached.

## Questions?

Reach out at [support@keygen.sh](mailto:support@keygen.sh) if you have any
questions or concerns!
