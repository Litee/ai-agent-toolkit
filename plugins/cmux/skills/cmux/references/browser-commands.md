# cmux Browser Commands Reference

All browser commands use the form: `cmux browser <surface> <subcommand> [args...]`

## Open & Navigate

**IMPORTANT:** `open-split --url` is unreliable — the URL often fails to load on initial creation.
Always use a two-step approach: create the split first, then navigate separately with a small delay:

```bash
# Two-step open (reliable)
cmux browser <surface> open-split --direction <dir>  # 1. create the split (note the returned surface ref)
sleep 1 && cmux browser <new-surface> navigate <url> # 2. navigate after surface is ready

# Single-surface commands
cmux browser <surface> open <url>                    # open URL in existing surface
cmux browser <surface> navigate <url>                # navigate to URL
cmux browser <surface> back                          # go back
cmux browser <surface> forward                       # go forward
cmux browser <surface> reload                        # reload page
cmux browser <surface> url                           # get current URL
cmux browser <surface> get title                     # get page title
```

## DOM Inspection

```bash
cmux browser <surface> snapshot [--selector <sel>] [--compact] [--max-depth <n>]  # get DOM snapshot
cmux browser <surface> get text <selector>           # get element text
cmux browser <surface> get html <selector>           # get element HTML
cmux browser <surface> get value <selector>          # get element value
cmux browser <surface> get attr <selector> --attr <name>  # get attribute
cmux browser <surface> get count <selector>          # count matching elements
cmux browser <surface> get box <selector>            # get bounding box
cmux browser <surface> get styles <selector>         # get CSS styles
cmux browser <surface> is visible <selector>         # check visibility
cmux browser <surface> is enabled <selector>         # check if enabled
cmux browser <surface> is checked <selector>         # check if checked
```

## Element Interaction

```bash
cmux browser <surface> click <selector>              # click element
cmux browser <surface> dblclick <selector>           # double-click
cmux browser <surface> hover <selector>              # hover
cmux browser <surface> focus <selector>              # focus element
cmux browser <surface> scroll-into-view <selector>   # scroll element into view
cmux browser <surface> scroll [--dy <pixels>]        # scroll page
```

## Form Input

```bash
cmux browser <surface> type <selector> "text"        # type into element (appends)
cmux browser <surface> fill <selector> "text"        # fill element (clears first)
cmux browser <surface> check <selector>              # check checkbox
cmux browser <surface> uncheck <selector>            # uncheck checkbox
cmux browser <surface> select <selector> "value"     # select dropdown value
cmux browser <surface> press <key>                   # press key (Enter, Tab, Escape, etc.)
```

## Find Elements (Locators)

```bash
cmux browser <surface> find role <role> [--name <name>]      # find by ARIA role
cmux browser <surface> find text "text" [--exact]            # find by text content
cmux browser <surface> find label "label" [--exact]          # find by label
cmux browser <surface> find placeholder "text" [--exact]     # find by placeholder
cmux browser <surface> find testid "id"                      # find by test ID
cmux browser <surface> find first <selector>                 # first match
cmux browser <surface> find nth <index> <selector>           # nth match
```

## JavaScript & Screenshots

```bash
cmux browser <surface> eval "document.title"         # evaluate JavaScript
cmux browser <surface> screenshot [--out <path>]     # take screenshot
```

## Wait for Conditions

```bash
cmux browser <surface> wait <selector>               # wait for element
cmux browser <surface> wait --text "text"             # wait for text
cmux browser <surface> wait --url "url"               # wait for URL
cmux browser <surface> wait --load-state <state>      # wait for load state
cmux browser <surface> wait --function "js expr"      # wait for JS condition
```

## Console & Errors

```bash
cmux browser <surface> console list                  # list console messages
cmux browser <surface> errors list                   # list page errors
```

## Tabs, Cookies & Storage

```bash
cmux browser <surface> tab list                      # list browser tabs
cmux browser <surface> tab new [<url>]               # new browser tab
cmux browser <surface> cookies get [--domain <d>]    # get cookies
cmux browser <surface> cookies set <name> <value>    # set cookie
cmux browser <surface> storage local get [<key>]     # get localStorage
cmux browser <surface> storage local set <key> <val> # set localStorage
```

## Network & Emulation

```bash
cmux browser <surface> viewport <width> <height>     # set viewport size
cmux browser <surface> offline true|false             # toggle offline mode
cmux browser <surface> geolocation <lat> <lng>        # set geolocation
cmux browser <surface> network route <pattern> [--abort] [--body <resp>]  # mock network
cmux browser <surface> network requests              # get network requests
```
