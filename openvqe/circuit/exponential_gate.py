"""
Exponential Gates which are generated by (anti-)hermitian Operators
"""
from openvqe import typing, numbers
from openvqe import OpenVQEException
from openvqe.hamiltonian import QubitHamiltonian
from openvqe.circuit import QCircuit, Variable
from openvqe.circuit._gates_impl import ExponentialPauliGateImpl
from openvqe import numpy
from random import shuffle


class DecompositionABC:
    """
    implements a call operator which takes an (anti-)hermitian operator outputs
    a decomposed unitary
    """

    def __call__(self, generator: QubitHamiltonian, *args, **kwargs):
        raise OpenVQEException("Overwrite this")


class DecompositionFirstOrderTrotter:

    def __init__(self, steps: int, threshold: float = 0.0, join_components: bool = False,
                 randomize_component_order: bool = False, randomize: bool = False):
        """
        The Decomposition module implements a call operator which decomposes a set of QubitHamiltonians
         into ExponentialPauligates
        See the __call__ implementation for more
        :param steps: Trotter Steps
        :param threshold: neglect terms in the given Hamiltonians if their coefficients are below this threshold
        :param join_components: The QubitHamiltonians in the list given to __call__ are jointly trotterized
        :param randomize_component_order: randomize the component order before trotterizing
        :param randomize: randomize the trotter decomposition of each component
        this means the trotterization will be:
        Trotter([H_0, H_1]) = Trotter(exp(i(H_0+H_1)t)
        otherwise it will be
        Trotter([H_0, H_1]) = Trotter(exp(i(H_0))Trotter(epx(iH_1t))
        """
        self.steps = steps
        self.threshold = threshold
        self.join_components = join_components
        self.randomize_component_order = randomize_component_order
        self.randomize = randomize

    def __call__(self, generators: typing.List[QubitHamiltonian],
                 coeffs: typing.List[typing.Union[numbers.Number, Variable]] = None, *args, **kwargs) -> QCircuit:
        """
        See __init___ for effect of several parameters
        :param generators: Generators given as a list of QubitHamiltonians [H_0, H_1, ...]
        :param coeffs: coefficients for each generator (can be a variable)
        :return: Trotter(exp(iH_0*coeff_0))*Trotter(exp(iH_1*coeff_1))*... or Trotter(exp(i(H_0*coeff_0+H_1*coeff_1+...)) depeding on self.join_components
        """
        c = 1.0
        result = QCircuit()
        if self.join_components:
            for step in range(self.steps):
                if self.randomize_component_order:
                    shuffle(generators)
                for i, g in enumerate(generators):
                    if coeffs is not None: c = coeffs[i]
                    result += self.compile(generator=g, steps=1, factor=c / self.steps, randomize=self.randomize)
        else:
            if self.randomize_component_order:
                shuffle(generators)
            for i, g in enumerate(generators):
                if coeffs is not None: c = coeffs[i]
                result += self.compile(generator=g, factor=c, randomize=self.randomize)

        return result

    def compile(self, generator: QubitHamiltonian, steps: int = None, factor: float = 1.0, randomize: bool = False):
        if steps is None:
            steps = self.steps
        assert (generator.is_hermitian())
        circuit = QCircuit()
        factor = factor / steps
        for index in range(steps):
            paulistrings = generator.paulistrings
            if randomize:
                shuffle(paulistrings)
            for ps in paulistrings:
                value = ps.coeff
                # don't make circuit for too small values
                if len(ps) != 0 and not numpy.isclose(value, 0.0, atol=self.threshold):
                    circuit += ExponentialPauliGateImpl(paulistring=ps, angle=factor * value)

        return circuit
