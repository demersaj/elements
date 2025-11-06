# Changelog

All notable changes to the Chain element will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-XX

### Added
- Initial release of Prompt Chain element
- Support for multi-step prompt chaining (up to 10 steps)
- Configurable prompt templates with {input} and {previous} placeholders
- Support for multiple model types (local, OpenAI, Anthropic)
- Per-step model configuration
- Per-step temperature control
- Intermediate step outputs for debugging
- Final output with complete chain history
- Automatic state management between steps
- Integration with Frame-based data flow
