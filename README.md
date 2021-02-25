# rpz-mimic
Minimal rpz mimic implementation for old isc bind version, this is intended to be used for smoot transitions of old bind installation to an rpz esporting system you will need to include the generated named_inc.conf.

## At invocation the software will:
  - Download rpz zone with a dig axfr rpz.zone @server command
  - Write down a named_inc.conf
  - Write down a zone file for each A record listed in rpz zone
  - Invoke rndc reconfig to load zones
  - Save applied SOA to a raw state file

# Warning
This is not error proof, following steps are taken to prevent disruptions, however there's lot more to do to avoid untrapped exceptions preventing bind running fine.
  - named_inc files are saved with .epoch extension before rndc reconfig
  - named-checkconf is run before rndc reconfig
  - named-checkzone is run against each generated zone before rndc reconfig
  - named_inc are rolled back to previous version in case of named-checkconf or rndc recnfig failures

## Contributing
Not much contributing here, in the insane case you are willing to, next wanted feature are:
  - Check improvement for config files and named stability

# Known limitation
  * Single rpz server
  * Single rpz zone
  * Only A rewrite supported
  * Sublevel of A rewrites will be wilcarded
  * No incremental transfert
  * "Small" list support tested against 15k entries and 50 distnct address (list and content will be kept in memory as dictionary during work)

## Non Script Disclaimer
This is not a script, call it whatever you want but not script, alternative suggested name are:
  - this, thing
  - stuff, gudget, gimmik
  - program, scheduled job
  - integration, automation, project

## Programming language fellowship campaign
Stop this meaningless dissing between different programming languages, coding language is a matter of comfort, if you love a different language you are encuraged to translate this code in any language you love.
