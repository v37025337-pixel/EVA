"""Fitness must measure the supplied genome, including expression settings."""
import copy
import unittest

from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1, _digest


class GenomeFitnessBindingTests(unittest.TestCase):
    def setUp(self):
        self.parent = YADOEvolutionaryGenomeV1.parent_genome(
            'a' * 64, {name: 'b' * 64 for name in ('LOGIC', 'THINKING', 'INTELLIGENCE', 'CODE')}
        )
        controller = YADOEvolutionaryGenomeV1(self.parent)
        self.child = controller.mutate({
            name: {'deficit': True, 'signature': 'AUDIT_TEST_DEFICIT'}
            for name in self.parent['chromosomes']
        })

    @staticmethod
    def seal(genome):
        for gene in genome['chromosomes'].values():
            gene['gene_digest'] = _digest({k: v for k, v in gene.items() if k != 'gene_digest'})
        genome['genome_digest'] = _digest({k: v for k, v in genome.items() if k != 'genome_digest'})
        return genome

    def test_identical_genomes_cannot_gain_fitness(self):
        result = YADOEvolutionaryGenomeV1.evaluate(self.parent, copy.deepcopy(self.parent))
        self.assertEqual(result['parent'], result['child'])
        self.assertEqual(result['fitness_gain'], 0.0)

    def test_swapping_genomes_swaps_measured_scores(self):
        forward = YADOEvolutionaryGenomeV1.evaluate(self.parent, self.child)
        backward = YADOEvolutionaryGenomeV1.evaluate(self.child, self.parent)
        self.assertEqual(forward['parent'], backward['child'])
        self.assertEqual(forward['child'], backward['parent'])
        self.assertGreater(forward['fitness_gain'], 0)
        self.assertEqual(forward['fitness_gain'], -backward['fitness_gain'])
        self.assertTrue(forward['all_regressions_pass'])

    def test_reduced_gene_expression_changes_measured_capability(self):
        weaker = copy.deepcopy(self.child)
        weaker['chromosomes']['LOGIC']['expression']['max_width'] = 1
        weaker['chromosomes']['INTELLIGENCE']['expression']['max_trigger_width'] = 2
        weaker['chromosomes']['CODE']['expression']['max_degree'] = 1
        self.seal(weaker)
        result = YADOEvolutionaryGenomeV1.evaluate(self.child, weaker)
        for organ in ('LOGIC', 'INTELLIGENCE', 'CODE'):
            self.assertGreater(result['parent'][organ], result['child'][organ], organ)
        self.assertLess(result['fitness_gain'], 0)

    def test_unknown_incompatible_or_unbound_genomes_are_rejected(self):
        unknown = copy.deepcopy(self.child)
        unknown['chromosomes']['LOGIC']['gene_id'] = 'NO_EXECUTABLE_IMPLEMENTATION'
        incompatible = copy.deepcopy(self.child)
        incompatible['chromosomes']['LOGIC'] = copy.deepcopy(incompatible['chromosomes']['CODE'])
        unsupported_expression = copy.deepcopy(self.child)
        unsupported_expression['chromosomes']['LOGIC']['expression']['max_width'] = 99
        missing = copy.deepcopy(self.child)
        del missing['chromosomes']['CODE']
        extra = copy.deepcopy(self.child)
        extra['chromosomes']['UNIMPLEMENTED'] = copy.deepcopy(extra['chromosomes']['CODE'])
        tampered = copy.deepcopy(self.child)
        tampered['chromosomes']['LOGIC']['expression']['max_width'] = 1
        cases = [None, {}, self.seal(unknown), self.seal(incompatible),
                 self.seal(unsupported_expression), self.seal(missing), self.seal(extra), tampered]
        for genome in cases:
            with self.subTest(genome=genome):
                with self.assertRaises(ValueError):
                    YADOEvolutionaryGenomeV1.evaluate(self.parent, genome)

    def test_real_evolution_call_remains_bound_to_its_child(self):
        result = YADOEvolutionaryGenomeV1(self.parent).evolve_once()
        replay = YADOEvolutionaryGenomeV1.evaluate(self.parent, result['child'])
        self.assertEqual(result['fitness'], replay)
        self.assertEqual(result['selection'], 'CHILD')
        self.assertFalse(result['promotion_authorized'])

    def test_evolved_parent_does_not_replay_canonical_parent_deficits(self):
        controller = YADOEvolutionaryGenomeV1(self.child)
        deficits = controller.observe_parent_deficits()
        self.assertTrue(all(not row['deficit'] for row in deficits.values()))
        result = controller.evolve_once()
        self.assertEqual(result['fitness']['fitness_gain'], 0.0)
        self.assertEqual(result['child']['mutation_count'], 0)
        self.assertEqual(result['selection'], 'PARENT')


if __name__ == '__main__':
    unittest.main()
