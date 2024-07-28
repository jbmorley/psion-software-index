# Psion Software Index

[![build](https://github.com/jbmorley/psion-software-index/actions/workflows/build.yaml/badge.svg)](https://github.com/jbmorley/psion-software-index/actions/workflows/build.yaml)

Tools for generating an index of Psion software

## Usage

Install the dependencies:

```
./install-dependencies.sh
```

Run the script:

```
./build.sh
```

## Development

For development, it can be useful to be able to run the indexer on a smaller library. For example,

```
./dumpapps library_small.yaml
```

N.B. You will need to have run the full built-out at least once to ensure you have the assets available locally.

## Contributing

Contributions are welcome in the form of PRs or GitHub Issues.

## References

- [Psion Software (Internet Archive)](https://archive.org/search?query=Psion)
