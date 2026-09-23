# General
* [x] Cleanup Repo branches locally and remotely
* [x] Report or fix cache issue with downlaods (old filter shown by browser, instead of newly applied filter)
* [x] Create PR for upstream for longRunningFilter extension and filter processing ux improvement

# AI Filter Plugins
* [x] Add _random StylePrompt which can be used in actions to let the plugin randomly choose any of the enabled user prompts
  * [x] Add random StylePrompt to config.py
  * [x] Add random logic to "applyFilter"
  * [x] Skip cache creation for random and custom logic
* [x] Create tests for gemini plugin
* [ ] Change "custom" prompt to access prompt from filter plugin folder, instead of config
* [ ] Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
* [ ] Move testing ipynb out off Gemini and make it general for all supported providers
* [ ] Explore locally hosted options like ComfyUI
* [ ] Create aggregate plugin with multiple vendor support