# Changelog

All notable changes to the Routing element will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-01-XX

### Changed
- Reduced number of outputs from 5 to 2 (route1 and route2)
- Updated routing function normalization to only handle route1 and route2
- Updated documentation to reflect two-output routing

## [0.1.0] - 2025-01-XX

### Added
- Initial release of the Routing element
- Support for routing input frames to one of two outputs (route1 or route2)
- Python-based routing function evaluation
- Flexible route identifier support (strings and integers)
- Automatic route identifier normalization
- Function compilation and caching for performance
- Comprehensive error handling and logging
- Full Frame object access in routing functions

### Features
- Routes input data based on user-defined Python routing logic
- Supports 2 different output routes
- Enables dynamic workflow routing and conditional branching
- Allows routing to specialized models or prompt chains based on frame content
