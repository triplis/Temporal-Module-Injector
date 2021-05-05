# Debug logging can be used in testing to check things like 
# whether a tuning was injected to without issues
# (such as breaking it, changing its type, etc.)
# by printing the entire attribute out with contents changed.
# This should be disabled in the release script to reduce
# information 'noise' in logging when investigating live issues.
# Most live issues are likely going to be caused by patch changes
# and we don't want a massive info dump log file to sift through.
DEBUG_ON = True