# dovecot-autoresponder
Small script that can trigger customizable, automatic email repsonses from
within Dovecot/sieve scripts.

## Installation
Configure Dovecot to allow execution of script through the extprogram plugin.
Include into `/etc/dovecot/conf.d/90-sieve.conf`:

```
sieve_plugins = sieve_extprograms
sieve_extensions = +vnd.dovecot.execute
```

And in `/etc/dovecot/conf.d/90-sieve-extprograms.conf`:

```
sieve_execute_bin_dir = /usr/lib/dovecot/sieve-execute
```

Then, copy `autoresponder.py` into the specified directory
(`/usr/lib/dovecot/sieve-execute` in this case), make it owned by root:root and
give it 0755 permissions.

Now in your user's sieve script, you need to require the execution plugin:

```
require ["fileinto","imap4flags","vnd.dovecot.execute"];
```

Then, you can simply specify rules:

```
if header :contains "to" ["foo@bar.com","bar@foo.com"]
{
	addflag "\\Seen";
	fileinto "Some Spam";
	execute :input "spamresponder" "autoresponder.py";
	stop;
}
```

The identifier given (in this case `spamresponder`) refers to the identifier
given to the autoresponder script on the command line. You can try it out by
running (as your local user):

```
$ echo spamresponder | SENDER=my@email.invalid.com /usr/lib/dovecot/sieve-execute/autoresponder.py
```

This will trigger the "spamresponder" action, as specified by the database
entry in `~/.mail/autoresponder.sqlite3` (the database is created on first
running the script). There is a "test" action defined that you can try out to
get a feeling for it.

## License
GNU GPL-3.
