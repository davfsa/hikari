# Copyright (c) 2020 Nekokatt
# Copyright (c) 2021 davfsa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
rm -rf public
mkdir public

nox -s pdoc
cd public/docs || exit 1

git init
git config user.name "github-actions"
git config user.email "github-actions@github.com"
git remote add origin "https://github-actions:${GITHUB_TOKEN}@github.com/hikari-py/hikari-py.github.io"

git checkout -B "task/docs-${VERSION}"
git add -Av .
git commit -am "Documentation for ${VERSION}"
git push -u origin "task/docs-${VERSION}"

curl \
  -X POST \
  -u "github-actions:${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  /repos/hikari-py/hikari-py.github.io/actions/workflows/pages/dispatches \
  -d '{"ref": '"task/docs-${VERSION}"', "inputs": {"version": '"${VERSION}"'}}'
