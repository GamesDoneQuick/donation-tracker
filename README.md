See setup instructions in the top level repository: https://github.com/GamesDoneQuick/donation-tracker-toplevel

## Contributing

### `pre-commit`

This project uses [`pre-commit`](https://pre-commit.com/) to run linters and other checks before every commit.

`pre-commit` has been added as part of `requirements.txt`, so new installs should automatically get it, but if not, you can get it manually with pip, and then install the hooks with the `pre-commit` binary.

```
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```

And now every time you `git commit` or `git push`, the appropriate checks will run!

_Note:_ You _can_ bypass these checks by adding `--no-verify` when you commit or push, though this is highly discouraged in most cases. In the future, CI tests may fail if any of these checks are not satisfied.

If the pre-commit hooks fail on your first commit with them, make sure you are not inside of a submodule! This can affect where `pre-commit` tries to install hooks, and cloning the tools (specifically, `black`) can cause an error.

To avoid this, clone this repo separately to a new folder (not as a submodule), run `pre-commit install`, and make a fake commit to get the environment tools installed. These tools are globalized, so going back and committing from the submodule copy should now work!
