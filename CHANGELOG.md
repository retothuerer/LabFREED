## Change Log
### v0.2.12
- bugfix:no warning message if PAC-CAT has same segment key in two segments

### v0.2.11
- bugfix:added missing well known segment key '250'
  
### v0.2.10
- bugfix:added missing well known segment key '20'
  
### v0.2.9
- bugfix in serialization of PAC-CAT with multiple categories
  
### v0.2.8
- option to pass cache to resolver for speedier check of service availability

### v0.2.7
- Improved README. No functional changes
  
### v0.2.6
- PAC_ID.to_url() preserves the identifier as is by default but allows to force short or long notation.
- PAC-ID Resolver does not try to resolve PAC-CAT with CIT v1.
  
### v0.2.5
- resolvers checks service states by default
- improvements and bugfixes in conversion from python types to TREX
- follow better naming conventions in CIT v1 
  
### v0.2.4
- improvements in formatting of validation messages
- bugfix in DataTable
 
### v0.2.3
- improvements in formatting of validation messages
- bugfix in DisplayNameExtension
  
### v0.2.2
- minor changes for better access of subfunctions. No change in existing API
  
### v0.2.1
- improved docu. no code changes

### v0.2.0b2
- improvements in api consistency and ease of use
- restructured code for better separation of concerns
- support for coupling information table v1

### v0.1.1
- minor internal improvements and bugfixes
  
### v0.1.0
- DRAFT Support for PAC-ID Resolver

### v0.0.20
- bugfix in TREX table to dict conversion
- markdown compatible validation printing 

### v0.0.19
- supports PAC-ID, PAC-CAT, TREX and DisplayName
- QR generation 
- ok-ish test coverage



