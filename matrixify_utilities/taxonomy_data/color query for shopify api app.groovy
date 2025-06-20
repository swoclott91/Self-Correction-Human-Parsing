query GetColorAndPatternValues {
  taxonomy {
    categories(first: 20) {
      edges {
        node {
          id
          name
          attributes(first: 10) {
            edges {
              node {
                ... on TaxonomyChoiceListAttribute {
                  id
                  name
                  values(first: 50) {
                    edges {
                      node {
                        id
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
