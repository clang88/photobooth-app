# General
* [x] Cleanup Repo branches locally and remotely
* [ ] Report or fix cache issue with downlaods (old filter shown by browser, instead of newly applied filter)
* [ ] Create PR for upstream for longRunningFilter extension and filter processing ux improvement

# AI Filter Plugins
* [ ] Add _random StylePrompt which can be used in actions to let the plugin randomly choose any of the enabled user prompts
  * [x] Add random StylePrompt to config.py
  * [x] Add random logic to "applyFilter"
  * [x] Skip cache creation for random and custom logic
* [ ] Create tests for gemini plugin
* [ ] Move testing ipynb out off Gemini and make it general for all supported providers
* [ ] Explore locally hosted options like ComfyUI
* [ ] Create aggregate plugin with multiple vendor support