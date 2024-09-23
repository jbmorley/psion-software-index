---
title: API
---

# API

## Version 1

The Psion Software Index provides a basic API in the form of static JSON files offering a structured data form of the index.

### Programs

```txt
https://software.psion.info/api/v1/programs/
```

### Summary

```txt
https://software.psion.info/api/v1/summary/
```

#### Example Output

```
{
    "installerCount": 11034,
    "uidCount": 5757,
    "versionCount": 6582,
    "shaCount": 8546
}
```

### Sources

Details of the sources used to compile the index:

```txt
https://software.psion.info/api/v1/sources/
```

#### Example Output

```json
[
    {
        "path": "/home/runner/work/psion-software-index/psion-software-index/_assets/3-libjune-05/3LIBJUNE05.iso",
        "name": "Psion 3-Lib Shareware Library June 2005",
        "description": "CD of the Psion 3-Lib\u00a0Shareware\u00a0library for Psion PDA's\u00a0",
        "url": "https://archive.org/download/3-libjune-05/3LIBJUNE05.iso",
        "html_url": "https://archive.org/details/3-libjune-05"
    },
    {
        "path": "/home/runner/work/psion-software-index/psion-software-index/_assets/diamond_mako/Mako.iso",
        "name": "Diamond Mako CD",
        "description": "<div>Original CD for Diamond Mako (Psion Revo Plus).</div><div><br /></div><div>This CD contains many programs to help you make better use of your Diamond Mako.\u00a0</div><div><br /></div><div><div>-----</div>Here is the original disk image in NRG (Nero) format and the converted to ISO version file</div>",
        "url": "https://archive.org/download/diamond_mako/Mako.iso",
        "html_url": "https://archive.org/details/diamond_mako"
    }
]

```
