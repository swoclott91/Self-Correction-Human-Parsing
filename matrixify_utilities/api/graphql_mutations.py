# Product Queries
GET_PRODUCT_QUERY = """
query getProduct($id: ID!) {
    product(id: $id) {
        id
        title
        description
        category {
            id
            name
            fullName
        }
        metafields(first: 50) {
            nodes {
                namespace
                key
                value
            }
        }
        properties {
            key
            value
        }
    }
}
"""

GET_PRODUCTS_QUERY = """
query getProducts($first: Int, $after: String, $query: String) {
    products(first: $first, after: $after, query: $query) {
        nodes {
            id
            title
            description
            createdAt
            updatedAt
            category {
                id
                name
                fullName
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

# Mutations
PRODUCT_UPDATE_MUTATION = """
mutation productUpdate($input: ProductInput!) {
    productUpdate(input: $input) {
        product {
            id
            title
            category {
                id
                name
                fullName
            }
            metafields(first: 50) {
                nodes {
                    namespace
                    key
                    value
                    type
                }
            }
            properties {
                key
                value
            }
        }
        userErrors {
            field
            message
        }
    }
}
""" 