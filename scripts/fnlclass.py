#!/usr/bin/env python3

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Florian Leitner <florian.leitner@gmail.com>"
__verison__ = "1.0"

from sklearn.externals.joblib import load

from fnl.stat.textclass import Data


def Predict(sentences, data, model_i, model_e):
    """Predict lables for `data` using a sklearn `pipeline`."""
    labels_i = model_i.predict(data.instances)
    labels_e = model_e.predict(data.instances)

    for idx in range(len(labels_i)):
        if not labels_i[idx] and not labels_e[idx]:
            label = 3
        elif not labels_e[idx]:
            label = 2
        elif not labels_i[idx]:
            label = 1
        else:
            label = 0

        print(label, sentences[idx], end='', sep='\t')


if __name__ == '__main__':

    # Program Setup
    # =============

    import argparse
    parser = argparse.ArgumentParser(description="a text classification tool")

    parser.add_argument("i_model", metavar='IN_MODEL',
                        help="interaction classifier model name")
    parser.add_argument("e_model", metavar='EV_MODEL',
                        help="evidence classifier model name")
    parser.add_argument("text", metavar='PLAIN_TEXT', type=open,
                        help="file containing the plain-text instances")
    parser.add_argument("tags", metavar='TAGGED_TEXT', type=open,
                        help="file containing the tagged instances")

    # Argument Parsing
    # ================

    args = parser.parse_args()

    data = Data(args.tags, column=2)
    sentences = args.text.readlines()
    Predict(sentences, data, load(args.i_model), load(args.e_model))
